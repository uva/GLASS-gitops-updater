import base64
import io
import json
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

import pytest

from gitops_updater.providers.bitbucket import BitbucketProvider, _NoRedirects


@pytest.fixture
def provider(tmp_path):
    token = tmp_path / "token"
    token.write_text("test-token\n", encoding="utf-8")
    provider = BitbucketProvider(str(token), "release/test", "workspace/repo")
    provider.client = MagicMock()
    return provider


def reply(payload):
    if isinstance(payload, dict):
        payload = json.dumps(payload).encode()
    return io.BytesIO(payload)


def responses(provider, *payloads):
    provider.client.open.side_effect = [
        payload if isinstance(payload, Exception) else reply(payload)
        for payload in payloads
    ]


HEAD = {"target": {"hash": "abc123"}}
FILE = {"type": "commit_file", "attributes": []}


def http_error(status):
    return HTTPError("https://api.bitbucket.org", status, "private detail", {}, None)


def last_request(provider):
    return provider.client.open.call_args.args[0]


def test_reads_utf8_at_resolved_branch_revision(provider):
    responses(provider, HEAD, FILE, "tag: café\n".encode())
    file = provider.get_file("apps\\my app#1.yaml")
    assert file.content() == "tag: café\n"
    assert file.path == "apps/my app#1.yaml"
    assert file.revision == "abc123"
    calls = provider.client.open.call_args_list
    assert calls[0].args[0].full_url.endswith("/refs/branches/release%2Ftest")
    assert (
        calls[1]
        .args[0]
        .full_url.endswith("/src/abc123/apps/my%20app%231.yaml?format=meta")
    )
    assert calls[2].args[0].full_url.endswith("/src/abc123/apps/my%20app%231.yaml")
    for call in calls:
        assert call.args[0].get_header("Authorization") == "Bearer test-token"
        assert call.kwargs == {"timeout": 30}


def test_api_token_uses_email_and_basic_auth(tmp_path):
    token = tmp_path / "token"
    token.write_text("api-token\n")
    provider = BitbucketProvider(
        str(token), "main", "workspace/repo", "bot@example.com"
    )
    provider.client = MagicMock()
    responses(provider, HEAD, FILE)
    assert provider.file_exists("app.yaml")
    expected = base64.b64encode(b"bot@example.com:api-token").decode()
    assert last_request(provider).get_header("Authorization") == f"Basic {expected}"


def test_missing_file_returns_false(provider):
    responses(provider, HEAD, http_error(404))
    assert not provider.file_exists("missing.yaml")


def test_get_missing_file_fails(provider):
    responses(provider, HEAD, http_error(404))
    with pytest.raises(FileNotFoundError):
        provider.get_file("missing.yaml")


def test_missing_branch_is_not_a_missing_file(provider):
    responses(provider, http_error(404))
    with pytest.raises(RuntimeError, match="HTTP 404"):
        provider.file_exists("app.yaml")


@pytest.mark.parametrize("status", [301, 401, 403, 429, 500])
def test_metadata_errors_are_not_missing_files(provider, status):
    responses(provider, HEAD, http_error(status))
    with pytest.raises(RuntimeError, match=f"HTTP {status}") as error:
        provider.file_exists("app.yaml")
    assert "private detail" not in str(error.value)
    assert "test-token" not in str(error.value)


@pytest.mark.parametrize("error", [URLError("private detail"), TimeoutError()])
def test_connection_errors_are_sanitized(provider, error):
    responses(provider, error)
    with pytest.raises(RuntimeError, match="connection or timeout"):
        provider.get_file("app.yaml")


@pytest.mark.parametrize(
    "metadata",
    [{"type": "commit_directory"}, {**FILE, "attributes": ["link"]}],
)
def test_non_regular_files_are_rejected(provider, metadata):
    responses(provider, HEAD, metadata)
    with pytest.raises(ValueError):
        provider.get_file("app.yaml")


def test_create_file_encodes_content_and_avoids_reserved_field_names(provider):
    responses(provider, HEAD, http_error(404), HEAD, b"")
    provider.create_file("message", "tag: café & +\n", "Create app")
    request = last_request(provider)
    assert request.get_method() == "POST"
    assert request.full_url.endswith("/src")
    assert parse_qs(request.data.decode()) == {
        "branch": ["release/test"],
        "parents": ["abc123"],
        "message": ["Create app"],
        "/message": ["tag: café & +\n"],
    }


def test_create_does_not_overwrite_existing_file(provider):
    responses(provider, HEAD, FILE)
    with pytest.raises(FileExistsError):
        provider.create_file("app.yaml", "content", "Create app")
    assert provider.client.open.call_count == 2


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_mutates_file_on_configured_branch(provider, operation):
    responses(provider, HEAD, FILE, b"old", HEAD, b"")
    file = provider.get_file("app.yaml")
    if operation == "update":
        provider.update_file(file, "Update app", "new")
    else:
        provider.delete_file(file, "Delete app")
    data = parse_qs(last_request(provider).data.decode())
    assert data["branch"] == ["release/test"]
    assert data["parents"] == ["abc123"]
    if operation == "update":
        assert data["/app.yaml"] == ["new"]
        assert data["message"] == ["Update app"]
    else:
        assert data["files"] == ["/app.yaml"]
        assert data["message"] == ["Delete app"]


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_changed_branch_prevents_commit(provider, operation):
    changed = {"target": {"hash": "def456"}}
    if operation == "create":
        responses(provider, HEAD, http_error(404), changed)
        action = lambda: provider.create_file("app.yaml", "new", "Create")
    else:
        responses(provider, HEAD, FILE, b"old", changed)
        file = provider.get_file("app.yaml")
        if operation == "update":
            action = lambda: provider.update_file(file, "Update", "new")
        else:
            action = lambda: provider.delete_file(file, "Delete")
    with pytest.raises(RuntimeError, match="branch changed"):
        action()
    assert all(
        call.args[0].get_method() == "GET"
        for call in provider.client.open.call_args_list
    )


def test_commit_failure_is_reported(provider):
    responses(provider, HEAD, http_error(404), HEAD, http_error(403))
    with pytest.raises(RuntimeError, match="HTTP 403"):
        provider.create_file("app.yaml", "new", "Create")


@pytest.mark.parametrize("path", ["", "../app.yaml", "apps/../app.yaml", "apps//app"])
def test_invalid_path_fails_before_network_access(provider, path):
    with pytest.raises(ValueError):
        provider.get_file(path)
    provider.client.open.assert_not_called()


@pytest.mark.parametrize(
    "repository", ["repo", "workspace/repo/extra", "/repo", "../repo"]
)
def test_invalid_repository_is_rejected(tmp_path, repository):
    with pytest.raises(ValueError, match="workspace/repository-slug"):
        BitbucketProvider(str(tmp_path / "unused"), "main", repository)


def test_empty_token_is_rejected(tmp_path):
    token = tmp_path / "token"
    token.write_text("\n")
    with pytest.raises(ValueError, match="token file"):
        BitbucketProvider(str(token), "main", "workspace/repo")


def test_redirects_are_not_followed():
    assert (
        _NoRedirects().redirect_request(None, None, 302, "", {}, "https://other")
        is None
    )
