from gitlab.v4.objects import ProjectFile

from gitops_updater.providers.gitprovider import GitProvider, GitFile
from gitlab import Gitlab, GitlabGetError


class GitLabFile(GitFile):
    def __init__(self, source: ProjectFile):
        self.source = source

    def content(self) -> str:
        return self.source.decode().decode()


class GitLabProvider(GitProvider):
    def __init__(self, url: str, token_path: str, branch: str, project: str):
        file = open(token_path, 'r')
        gitlab_token = file.read()
        file.close()

        self.client = Gitlab(url, private_token=gitlab_token)
        self.project = self.client.projects.get(project)
        self.branch = branch

    def file_exists(self, path: str) -> bool:
        try:
            self.project.files.get(file_path=path, ref=self.branch)
        except GitlabGetError:
            return False
        return True

    def get_file(self, path: str) -> GitFile:
        f = self.project.files.get(file_path=path, ref=self.branch)
        return GitLabFile(f)

    def create_file(self, path: str, content: str, message: str):
        self.project.files.create({
            'file_path': path,
            'branch': self.branch,
            'content': content,
            'commit_message': message
        })

    def update_file(self, gitfile: GitLabFile, message: str, content: str):
        gitfile.source.content = content
        gitfile.source.save(branch=self.branch, commit_message=message)

    def delete_file(self, gitfile: GitLabFile, message: str):
        gitfile.source.delete(branch=self.branch, commit_message=message)
