# Gunicorn config variables
loglevel = "info"
errorlog = "-"  # stderr
accesslog = "-"  # stdout
worker_tmp_dir = "/tmp"
graceful_timeout = 120
timeout = 120
keepalive = 5
threads = 1