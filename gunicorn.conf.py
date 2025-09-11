# Gunicorn configuration file for NuviaButik
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help limit memory leaks
max_requests = 1000
max_requests_jitter = 50

# Log to stdout so Docker can capture logs
accesslog = "/var/log/gunicorn/nuviabutik_access.log"
errorlog = "/var/log/gunicorn/nuviabutik_error.log"
loglevel = "info"

# Process naming
proc_name = "nuviabutik_gunicorn"

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/nuviabutik.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# SSL (if you're using SSL termination at Gunicorn level)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
