from dataclasses import dataclass

from ruamel.yaml import YAML

from gitops_updater.providers.github import GitHubProvider


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
            for row in yamlfile['config']:
                if row['name'] == name:
                    return ConfigEntry(
                        row['name'],
                        row['path'],
                        row['secretPath'],
                        row['handler'],
                        row['provider']
                    )

        raise Exception("Couldn't read config")

    def find_provider(self, filename: str, name: str):
        yaml = YAML()
        with open(filename, 'r') as file:
            yamlfile = yaml.load(file)
            for row in yamlfile['providers']:
                if row['name'] == name and row['type'] == 'GitHub':
                    return GitHubProvider(row['tokenPath'], row['branch'], row['repository'])

        raise Exception("Couldn't read config")
