import base64
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from gitops_updater.providers.gitprovider import GitFile, GitProvider


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward credentials to redirects (including LFS downloads).
        return None


@dataclass
class BitbucketFile(GitFile):
    path: str
    revision: str
    text: str

    def content(self) -> str:
        return self.text


class BitbucketProvider(GitProvider):
    def __init__(
        self, token_path: str, branch: str, repository: str, email: str | None = None
    ):
        parts = repository.split("/")
        if len(parts) != 2 or any(part in ("", ".", "..") for part in parts):
            raise ValueError("Bitbucket repository must be workspace/repository-slug")
        if not branch.strip():
            raise ValueError("Bitbucket branch must not be empty")
        with open(token_path, encoding="utf-8") as file:
            token = file.read().strip()
        if not token:
            raise ValueError("Bitbucket token file must not be empty")

        self.url = "https://api.bitbucket.org/2.0/repositories/" + "/".join(
            quote(part, safe="") for part in parts
        )
        self.branch = branch
        if email is not None:
            if not email.strip():
                raise ValueError("Bitbucket email must not be empty")
            credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
            self.authorization = f"Basic {credentials}"
        else:
            self.authorization = f"Bearer {token}"
        self.client = build_opener(_NoRedirects())

    def _request(self, path: str, data: dict | None = None, missing_ok=False):
        request = Request(
            self.url + path,
            data=urlencode(data).encode("utf-8") if data is not None else None,
            headers={"Authorization": self.authorization},
        )
        try:
            with self.client.open(request, timeout=30) as response:
                return response.read()
        except HTTPError as error:
            status = error.code
            error.close()
            if status == 404 and missing_ok:
                return None
            # The API route returns exception messages to callers. Never include
            # upstream response bodies or credentials in these messages.
            raise RuntimeError(f"Bitbucket request failed (HTTP {status})") from None
        except (URLError, TimeoutError):
            raise RuntimeError(
                "Bitbucket request failed (connection or timeout)"
            ) from None

    def _head(self) -> str:
        result = self._request("/refs/branches/" + quote(self.branch, safe=""))
        return json.loads(result)["target"]["hash"]

    @staticmethod
    def _path(path: str) -> str:
        # Template paths can originate on Windows; Git always uses '/' paths.
        path = path.replace("\\", "/").lstrip("/")
        if not path or any(part in ("", ".", "..") for part in path.split("/")):
            raise ValueError("Bitbucket file path must identify a repository file")
        return path

    def _metadata(self, path: str, revision: str):
        result = self._request(
            f"/src/{quote(revision, safe='')}/{quote(path, safe='/')}?format=meta",
            missing_ok=True,
        )
        if result is None:
            return None
        metadata = json.loads(result)
        if metadata["type"] != "commit_file":
            raise ValueError("Bitbucket path is not a file")
        # This provider updates plain YAML/templates, not links or executables.
        if metadata.get("attributes"):
            raise ValueError("Bitbucket file attributes are not supported")
        return metadata

    def file_exists(self, path: str) -> bool:
        return self._metadata(self._path(path), self._head()) is not None

    def get_file(self, path: str) -> BitbucketFile:
        path = self._path(path)
        revision = self._head()
        if self._metadata(path, revision) is None:
            raise FileNotFoundError("Bitbucket file does not exist")
        content = self._request(
            f"/src/{quote(revision, safe='')}/{quote(path, safe='/')}"
        )
        return BitbucketFile(path, revision, content.decode("utf-8"))

    def _commit(self, revision: str, message: str, changes: dict):
        if self._head() != revision:
            raise RuntimeError("Bitbucket branch changed; retry the update")
        self._request(
            "/src",
            {"branch": self.branch, "parents": revision, "message": message, **changes},
        )

    def create_file(self, path: str, content: str, message: str):
        path = self._path(path)
        revision = self._head()
        if self._metadata(path, revision) is not None:
            raise FileExistsError("Bitbucket file already exists")
        self._commit(revision, message, {f"/{path}": content})

    def update_file(self, gitfile: BitbucketFile, message: str, content: str):
        self._commit(
            gitfile.revision, message, {f"/{self._path(gitfile.path)}": content}
        )

    def delete_file(self, gitfile: BitbucketFile, message: str):
        self._commit(
            gitfile.revision, message, {"files": f"/{self._path(gitfile.path)}"}
        )
