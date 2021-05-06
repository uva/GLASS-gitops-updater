from ruamel.yaml import YAML

from ConfigEntry import ConfigEntry


class ConfigReader:
    def find(self, filename: str, name: str) -> ConfigEntry:
        yaml = YAML()
        with open(filename, 'r') as file:
            yamlfile = yaml.load(file)
            for row in yamlfile:
                if row['name'] == name:
                    return ConfigEntry(
                        row['name'],
                        row['repo'],
                        row['branch'],
                        row['manifest'],
                        row['secretPath']
                    )

        raise Exception("Couldn't read config")
