from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from gitops_updater.config import ConfigReader


@pytest.mark.parametrize(
    "provider_type,extra,expected",
    [
        (
            "GitHub",
            {"repository": "workspace/repo"},
            ("token", "main", "workspace/repo"),
        ),
        (
            "GitLab",
            {"url": "https://gitlab.com", "project": "group/project"},
            ("https://gitlab.com", "token", "main", "group/project"),
        ),
        (
            "Bitbucket",
            {"repository": "workspace/repo"},
            ("token", "main", "workspace/repo", None),
        ),
        (
            "Bitbucket",
            {"repository": "workspace/repo", "email": "bot@example.com"},
            ("token", "main", "workspace/repo", "bot@example.com"),
        ),
    ],
)
def test_provider_selection(tmp_path, provider_type, extra, expected):
    config = tmp_path / "config.yaml"
    YAML().dump(
        {
            "providers": [
                {"name": "unrelated", "type": "Unknown"},
                {
                    "name": "target",
                    "type": provider_type,
                    "branch": "main",
                    "tokenPath": "token",
                    **extra,
                },
            ]
        },
        config,
    )
    with patch(f"gitops_updater.config.{provider_type}Provider") as factory:
        result = ConfigReader().find_provider(str(config), "target")
    factory.assert_called_once_with(*expected)
    assert result is factory.return_value
