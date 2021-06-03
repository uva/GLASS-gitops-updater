import os.path
from dataclasses import dataclass

import jinja2

from gitops_updater.config import ConfigEntry
from gitops_updater.providers.gitprovider import GitProvider, GitFile


@dataclass
class Template:
    config: ConfigEntry
    provider: GitProvider

    def handle(self, id_: int, version: str) -> dict:

        target_path = self.get_target_path(self.config.path, id_)
        target_exists = self.provider.file_exists(target_path)

        template: GitFile
        template = self.provider.get_file(self.config.path)
        content = self.apply_template(template.content(), id_, version)

        if not target_exists:
            message = 'Create {}:{} with version {}'.format(self.config.name, id_, version)
            self.provider.create_file(target_path, content, message)
            return {'message': 'File created'}

        else:
            message = 'Update {}:{} to {}'.format(self.config.name, id_, version)
            file: GitFile
            file = self.provider.get_file(target_path)
            if file.content() == content:
                return {'message': 'Already up-to-date'}
            else:
                self.provider.update_file(file, message, content)
                return {'message': 'Version updated'}

    def apply_template(self, content: str, id_: int, version) -> str:
        tm = jinja2.Template(content)
        return tm.render(id=id_, version=version)

    def get_target_path(self, source_path: str, id_: int) -> str:

        directory = os.path.dirname(source_path)
        filename = os.path.basename(source_path)

        filename_segments = filename.split('.')
        filename_segments[0] = '{}-{}'.format(filename_segments[0], id_)

        return os.path.join(directory, '.'.join([segment for segment in filename_segments if segment != 'j2']))
