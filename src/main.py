import os

from flask import Flask, request, json

from ConfigReader import ConfigReader
from GitHubYamlFile import GitHubYamlFile

app = Flask(__name__)


def __json_response(status: int, payload):
    return app.response_class(response=json.dumps(payload), status=status, mimetype='application/json')


@app.route('/gitops-updater')
def handle():
    if 'CONFIG_PATH' not in os.environ:
        return __json_response(422, {'error': 'CONFIG_PATH not set'})
    if 'GITHUB_TOKEN_PATH' not in os.environ:
        return __json_response(422, {'error': 'GITHUB_TOKEN_PATH not set'})

    name = request.args.get('name')
    secret = request.args.get('secret')
    version = request.args.get('version')

    if name is None or secret is None or version is None:
        return __json_response(422, {'error': 'Missing GET-arguments'})

    try:
        config = ConfigReader().find(os.environ['CONFIG_PATH'], name)
        if not config.valid_secret(secret):
            return __json_response(422, {'error': 'Invalid secret'})

        github_file = GitHubYamlFile.create_from_config(os.environ['GITHUB_TOKEN_PATH'], config)
        github_file.check_target_version(version)
        github_file.update_version(version)

        return __json_response(200, {
            'message': f'updated successfully',
            'old_version': github_file.current_version,
            'new_version': version
        })

    except Exception as e:
        return __json_response(422, {'error': str(e)})


if __name__ == '__main__':
    app.run()
