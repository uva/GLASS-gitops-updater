from dataclasses import dataclass

from ruamel.yaml import YAML

from gitops_updater.providers.github import GitHubProvider
from gitops_updater.providers.gitlab import GitLabProvider


@dataclass
class ConfigEntry:
    name: str
    path: str
    secret_path: str
    handler: str
    provider: str

    def valid_secret(self, secret: str) -> bool:
        with open(self.secret_path, 'r') as file:
            stored_secret = file.read()
            return stored_secret == secret

    def secret(self) -> str:
        with open(self.secret_path, 'r') as file:
            return file.read()

class ConfigReader:
    def find(self, filename: str, name: str) -> ConfigEntry:
        yaml = YAML()
        with open(filename, 'r') as file:
            yamlfile = yaml.load(file)

            if 'config' not in yamlfile:
                raise Exception("Couldn't read config: Unable to locate config section")

            for row in yamlfile['config']:
                if row['name'] == name:
                    return ConfigEntry(
                        row['name'],
                        row['path'],
                        row['secretPath'],
                        row['handler'],
                        row['provider']
                    )

        raise Exception(f"Couldn't read config: Unable to locate entry with the name '{name}'")

    def find_provider(self, filename: str, name: str):
        yaml = YAML()
        with open(filename, 'r') as file:
            yamlfile = yaml.load(file)
            for row in yamlfile['providers']:
                if row['name'] == name:
                    if row['type'] == 'GitHub':
                        return GitHubProvider(row['tokenPath'], row['branch'], row['repository'])
                    if row['type'] == 'GitLab':
                        return GitLabProvider(row['url'], row['tokenPath'], row['branch'], row['project'])

                    raise Exception(f"Couldn't read config: Unable to resolve provider type '{row['type']}'")
                
        raise Exception(f"Couldn't read config: The provider with name '{name}' could not be found")
