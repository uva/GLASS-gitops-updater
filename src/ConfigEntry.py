from dataclasses import dataclass


@dataclass
class ConfigEntry:
    name: str
    repo: str
    branch: str
    manifest: str
    secret_path: str

    def valid_secret(self, secret: str) -> bool:
        with open(self.secret_path, 'r') as file:
            stored_secret = file.read()
            return stored_secret == secret
