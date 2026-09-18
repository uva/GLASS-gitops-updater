import unittest
from unittest.mock import MagicMock

from gitops_updater.config import ConfigEntry
from gitops_updater.handlers.fusion_archive import FusionArchive
from gitops_updater.providers.gitprovider import GitFile


class TestFusionArchive(unittest.TestCase):
    @staticmethod
    def _make_handler(content: str) -> tuple[FusionArchive, MagicMock]:
        mock_file = MagicMock(spec=GitFile)
        mock_file.content.return_value = content

        mock_provider = MagicMock()
        mock_provider.get_file.return_value = mock_file

        mock_config = MagicMock(spec=ConfigEntry)
        mock_config.path = "apps/mosaic-development.yaml"
        mock_config.name = "mosaic-development"

        handler = FusionArchive(config=mock_config, provider=mock_provider)
        return handler, mock_provider

    YAML_TEMPLATE = """\
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: mosaic-development
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  project: default

  source:
    repoURL: glass.azurecr.io
    chart: helm/mosaic
    targetRevision: 1.0.20260914204023

    helm:
      values: |
        hostname: api.glass-dev.ic.uva.nl
        ingressClass: nginx
        environmentName: development
        gateway:
          name: glass-dev
        mosaic:
          environment: Development
          reverseProxy:
            enabled: true
        fusionArchive:
          targetRevision: dev-1.0.20260918114007

  destination:
    server: https://kubernetes.default.svc
    namespace: mosaic-development

  syncPolicy:
    automated:
      prune: true
    syncOptions:
    - CreateNamespace=true
"""

    def test_updates_version(self):
        content = self.YAML_TEMPLATE.format(version="dev-1.0.20260918114007")
        handler, mock_provider = self._make_handler(content)

        result = handler.handle("dev-1.0.20260919000000")

        mock_provider.update_file.assert_called_once()
        _, _, updated_content = mock_provider.update_file.call_args.args
        self.assertIn("dev-1.0.20260919000000", updated_content)
        self.assertEqual(result["new_version"], "dev-1.0.20260919000000")
        self.assertEqual(result["old_version"], "dev-1.0.20260918114007")

    def test_already_up_to_date(self):
        content = self.YAML_TEMPLATE.format(version="dev-1.0.20260918114007")
        handler, mock_provider = self._make_handler(content)

        result = handler.handle("dev-1.0.20260918114007")

        mock_provider.update_file.assert_not_called()
        self.assertEqual(result["message"], "Already up-to-date")

    def test_raises_if_revision_not_found(self):
        content = "fusionArchive:\n          targetRevision: invalid-value\n"
        handler, _ = self._make_handler(content)

        with self.assertRaises(Exception, msg="fusionArchive.targetRevision not found"):
            handler.handle("dev-1.0.20260919000000")

    def test_all_environments(self):
        for env in ("dev", "acc", "sandbox", "prod"):
            with self.subTest(env=env):
                version = f"{env}-1.0.20260918114007"
                content = self.YAML_TEMPLATE.format(version=version)
                handler, mock_provider = self._make_handler(content)

                result = handler.handle(f"{env}-1.0.20260919000000")

                self.assertEqual(result["new_version"], f"{env}-1.0.20260919000000")

                _, _, updated_content = mock_provider.update_file.call_args.args
                self.assertIn(
                    f"fusionArchive:\n          targetRevision: {env}-1.0.20260919000000",
                    updated_content,
                )


if __name__ == "__main__":
    unittest.main()
