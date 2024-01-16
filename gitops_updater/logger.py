from urllib.parse import parse_qsl
from gunicorn.glogging import Logger as GunicornBaseLogger


class CustomGunicornLogger(GunicornBaseLogger):
    def access(self, resp, req, environ, request_time):
        parsed_query = parse_qsl(environ['QUERY_STRING'])

        for key, value in parsed_query:
            if key == "secret":
                redacted_secret = value[0:2] + ('*' * (len(value) - 3)) + value[-1] if len(value) > 3 else value
                environ['RAW_URI'] = environ['RAW_URI'].replace(value, redacted_secret, 1)

        super().access(resp, req, environ, request_time)
