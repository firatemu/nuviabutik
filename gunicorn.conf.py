# Gunicorn configuration — NuviaButik production
import multiprocessing
import os

bind = "127.0.0.1:8000"
backlog = 2048

cpus = multiprocessing.cpu_count()
# I/O ağırlıklı Django: az süreç, çok iş parçacığı (RAM dostu, yüksek eşzamanlılık)
workers = max(cpus, 3)
threads = 4
worker_class = "gthread"
worker_connections = 1000

timeout = 120
graceful_timeout = 30
keepalive = 5

max_requests = 5000
max_requests_jitter = 500

preload_app = True
reload = os.environ.get("GUNICORN_RELOAD", "0") == "1"

accesslog = "/var/log/gunicorn/nuviabutik_access.log"
errorlog = "/var/log/gunicorn/nuviabutik_error.log"
loglevel = "info"

proc_name = "nuviabutik_gunicorn"
daemon = False
pidfile = "/var/run/gunicorn/nuviabutik.pid"
user = "www-data"
group = "www-data"
