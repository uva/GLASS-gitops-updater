from dataclasses import dataclass

from ConfigEntry import ConfigEntry
from github import Github, ContentFile, Repository
from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO

import semver


@dataclass
class GitHubYamlFile:
    config: ConfigEntry
    repository: Repository
    content_file: ContentFile
    yaml_content: list
    yaml_segment: object
    current_version: str

    def check_target_version(self, target_version: str):
        target_version_semver = semver.VersionInfo.parse(target_version)
        current_version_semver = semver.VersionInfo.parse(self.current_version)

        if target_version_semver == current_version_semver:
            raise Exception(f'Not updating, version already {target_version_semver}')

        if current_version_semver > target_version_semver:
            raise Exception(f'Not downgrading to version {target_version_semver}')

    def update_version(self, target_version: str):

        self.yaml_segment['spec']['source']['targetRevision'] = target_version
        stream = StringIO()
        message = f'Update {self.config.name} to {target_version}'
        YAML().dump_all(self.yaml_content, stream)
        self.repository.update_file(self.content_file.path, message, stream.getvalue(), self.content_file.sha,
                                    branch=self.config.branch)

    @staticmethod
    def create_from_config(github_token_path: str, config: ConfigEntry):

        with open(github_token_path, 'r') as file:
            github_token = file.read()
            client = Github(github_token)
            repo = client.get_repo(config.repo)
            content = repo.get_contents(config.manifest, ref=config.branch)

            yamlloader = YAML()
            yamlcontent = list(yamlloader.load_all(content.decoded_content))

            for segment in yamlcontent:
                if segment['metadata'] is None or segment['metadata']['name'] != config.name:
                    continue

                current_version = segment['spec']['source']['targetRevision']

                return GitHubYamlFile(config, repo, content, yamlcontent, segment, current_version)

            raise Exception("Couldn't locate segment in yaml file")
