# Gunicorn configuration file for NuviaButik - OPTIMIZED
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes - OPTIMIZED
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"  # sync daha stabil, geventlet daha hızlı ama riskli
worker_connections = 1000
timeout = 60  # 30 -> 60 saniye (ağır işlemler için)
keepalive = 5  # 2 -> 5 saniye (persistent connections)

# Restart workers after this many requests, to help limit memory leaks
max_requests = 2000  # 1000 -> 2000 (daha az restart)
max_requests_jitter = 100  # 50 -> 100

# Preload app for faster worker spawn
preload_app = True

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
