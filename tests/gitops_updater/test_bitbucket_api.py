import io
import json
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs

import pytest
from ruamel.yaml import YAML

from gitops_updater.main import app


@pytest.mark.parametrize("version,commits", [("1.0.1", 1), ("1.0.0", 0)])
def test_existing_argocd_route_with_bitbucket(tmp_path, monkeypatch, version, commits):
    token = tmp_path / "token"
    token.write_text("bitbucket-test-token")
    secret = tmp_path / "secret"
    secret.write_text("caller-secret")
    config = tmp_path / "config.yaml"
    YAML().dump(
        {
            "providers": [
                {
                    "name": "bitbucket",
                    "type": "Bitbucket",
                    "repository": "workspace/repo",
                    "branch": "main",
                    "tokenPath": str(token),
                }
            ],
            "config": [
                {
                    "name": "example",
                    "path": "apps/example.yaml",
                    "handler": "argocd",
                    "provider": "bitbucket",
                    "secretPath": str(secret),
                }
            ],
        },
        config,
    )
    monkeypatch.setenv("CONFIG_PATH", str(config))
    client = MagicMock()
    head = json.dumps({"target": {"hash": "abc123"}}).encode()
    client.open.side_effect = [
        io.BytesIO(head),
        io.BytesIO(b'{"type": "commit_file", "attributes": []}'),
        io.BytesIO(
            b"metadata:\n  name: example\nspec:\n  source:\n"
            b"    chart: example\n    targetRevision: 1.0.0\n"
        ),
        io.BytesIO(head),
        io.BytesIO(b""),
    ]
    with patch("gitops_updater.providers.bitbucket.build_opener", return_value=client):
        response = app.test_client().get(
            "/gitops-updater",
            query_string={
                "name": "example",
                "secret": "caller-secret",
                "version": version,
            },
        )
    assert response.status_code == 200
    writes = [
        call.args[0]
        for call in client.open.call_args_list
        if call.args[0].get_method() == "POST"
    ]
    assert len(writes) == commits
    if commits:
        data = parse_qs(writes[0].data.decode())
        document = YAML().load(data["/apps/example.yaml"][0])
        assert document["spec"]["source"]["targetRevision"] == version
        assert document["spec"]["source"]["chart"] == "example"
        assert data["message"] == ["Update example to 1.0.1"]
        assert response.json["new_version"] == version
    else:
        assert response.json == {"message": "Already up-to-date"}
