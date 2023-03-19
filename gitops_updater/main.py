import hashlib
import hmac
import os

from flask import Flask, request, json

from gitops_updater.config import ConfigReader
from gitops_updater.handlers.argocd import ArgoCD
from gitops_updater.handlers.template import Template

app = Flask(__name__)


def __json_response(status: int, payload):
    return app.response_class(response=json.dumps(payload), status=status, mimetype='application/json')


@app.route('/gitops-updater')
def handle():
    if 'CONFIG_PATH' not in os.environ:
        return __json_response(422, {'error': 'CONFIG_PATH not set'})

    name = request.args.get('name')
    secret = request.args.get('secret')
    version = request.args.get('version')

    if name is None or secret is None or version is None:
        return __json_response(422, {'error': 'Missing GET-arguments'})

    try:
        config = ConfigReader().find(os.environ['CONFIG_PATH'], name)
        if not config.valid_secret(secret):
            return __json_response(422, {'error': 'Invalid secret'})

        provider = ConfigReader().find_provider(os.environ['CONFIG_PATH'], config.provider)

        if config.handler == 'template':

            id_ = request.args.get('id')
            if id_ is None:
                return __json_response(422, {'error': 'Missing GET-arguments'})

            id_ = int(id_)
            handler = Template(config, provider)

            if version == "delete":
                response = handler.handle_closed_pr(id_)
                return __json_response(200, response)
            else:
                response = handler.handle(id_, version)
                return __json_response(200, response)

        if config.handler == 'argocd':
            handler = ArgoCD(config, provider)
            response = handler.handle(version)

            return __json_response(200, response)
    except Exception as e:
        return __json_response(422, {'error': str(e)})


@app.route('/gitops-updater/webhooks/github', methods=['POST'])
def github_webhook():
    body = request.get_json()

    if 'action' not in body or 'number' not in body:
        return __json_response(422, {'error': 'Missing JSON-arguments'})

    if 'X-Hub-Signature-256' not in request.headers:
        return __json_response(422, {'error': 'Missing X-Hub-Signature-256 header'})

    if body['action'] != 'closed':
        return __json_response(200, {'message': 'action not closed, skipping'})

    if 'CONFIG_PATH' not in os.environ:
        return __json_response(422, {'error': 'CONFIG_PATH not set'})

    name = request.args.get('name')
    id_ = body['number']

    if name is None:
        return __json_response(422, {'error': 'Missing GET-arguments'})

    try:
        config = ConfigReader().find(os.environ['CONFIG_PATH'], name)

        expected = hmac.new(bytes(config.secret(), 'UTF-8'), request.data, hashlib.sha256).hexdigest()
        incoming = request.headers.get('X-Hub-Signature-256').split('sha256=')[-1].strip()
        if not hmac.compare_digest(incoming, expected):
            return __json_response(422, {'error': 'Invalid secret in X-Hub-Signature-256 header'})

        provider = ConfigReader().find_provider(os.environ['CONFIG_PATH'], config.provider)
        handler = Template(config, provider)
        response = handler.handle_closed_pr(id_)

        return __json_response(200, response)
    except Exception as e:
        return __json_response(422, {'error': str(e)})


if __name__ == '__main__':
    app.run()
