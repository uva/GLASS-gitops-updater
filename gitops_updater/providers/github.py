from github import Github, ContentFile
from github.GithubException import UnknownObjectException

from gitops_updater.providers.gitprovider import GitProvider, GitFile


class GitHubFile(GitFile):
    def __init__(self, source: ContentFile):
        self.source = source

    def content(self) -> str:
        return self.source.decoded_content.decode("utf-8")


class GitHubProvider(GitProvider):
    def __init__(self, token_path: str, branch: str, repository: str):

        file = open(token_path, 'r')
        github_token = file.read()
        file.close()

        self.client = Github(github_token)
        self.repo = self.client.get_repo(repository)
        self.branch = branch

    def file_exists(self, path) -> bool:
        try:
            self.repo.get_contents(path, ref=self.branch)
        except UnknownObjectException:
            return False

        return True

    def get_file(self, path) -> GitHubFile:
        content = self.repo.get_contents(path, ref=self.branch)
        return GitHubFile(content)

    def create_file(self, path: str, content: str, message: str):
        self.repo.create_file(path, message, content, branch=self.branch)

    def update_file(self, gitfile: GitHubFile, message: str, content: str):
        content_file: ContentFile
        content_file = gitfile.source
        self.repo.update_file(content_file.path, message, content, content_file.sha, branch=self.branch)

    def delete_file(self, gitfile: GitFile, message: str):
        content_file: ContentFile
        content_file = gitfile.source
        self.repo.delete_file(content_file.path, message, content_file.sha, branch=self.branch)