from dataclasses import dataclass

import re


@dataclass
class FusionArchive:
    _FUSION_ARCHIVE_REVISION_RE = re.compile(
        r'(fusionArchive:\s*\n\s+targetRevision:\s*)(?P<TargetRevision>(dev|acc|sandbox|prod)-(\d+\.\d+\.\d+))'
    )

    config: ConfigEntry
    provider: GitProvider

    def handle(self, target_version: str) -> dict:
        file: GitFile
        file = self.provider.get_file(self.config.path)

        current_content = file.content()
        current_version = self._get_current_version(current_content)

        if target_version == current_version:
            return {'message': 'Already up-to-date'}

        updated_content = self._update_version(current_content, target_version)
        message = f'Update {self.config.name} to {target_version}'
        self.provider.update_file(file, message, updated_content)

        return {
            'message': f'updated successfully',
            'old_version': current_version,
            'new_version': target_version
        }

    def _get_current_version(self, content: str) -> str:
        match = self._FUSION_ARCHIVE_REVISION_RE.search(content)
        if match is None:
            raise Exception(' fusionArchive.targetRevision not found')

        return match.group('TargetRevision')

    def _update_version(self, content: str, target_version: str) -> str:
        updated, count = self._FUSION_ARCHIVE_REVISION_RE.subn(
            rf'\g<TargetRevision>{target_version}',
            content
        )

        if count == 0:
            raise Exception('fusionArchive.targetRevision not found')

        return updated
