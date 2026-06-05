"""ReQCollect — Gunicorn configuration.

Gunicorn + uvicorn workers for production deployment.
Designed for Docker container usage with graceful shutdown.

Usage:
    gunicorn app.main:app -c gunicorn.conf.py
"""

import multiprocessing
import os

# ── Server socket ──
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:9900")
backlog = 2048

# ── Worker processes ──
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
graceful_timeout = 30
keepalive = 5

# ── Logging ──
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = "-"  # stdout
errorlog = "-"   # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# ── Process naming ──
proc_name = "reqcollect"
pidfile = None  # Don't write pidfile in container

# ── Docker friendly ──
# Prevent gunicorn from detaching (must stay in foreground)
daemon = False

# ── Graceful shutdown ──
# When gunicorn receives SIGTERM, it sends SIGTERM to workers,
# waits graceful_timeout, then sends SIGKILL
# Uvicorn workers handle SIGTERM by finishing current request
