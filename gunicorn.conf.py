"""Gunicorn settings (read automatically from the working directory)."""
import os

bind = "0.0.0.0:8080"
# One request per process: mission building keeps module-level state, so no threads.
# A mission takes about a second to build; a few workers keep the UI responsive meanwhile.
workers = int(os.environ.get("WEB_CONCURRENCY", "3"))
worker_class = "sync"
timeout = 120             # big missions with many flights and scripts
graceful_timeout = 30
preload_app = True        # load pydcs once and share it between workers
max_requests = 500        # recycle workers now and then so memory stays flat
max_requests_jitter = 50
accesslog = "-"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms'
