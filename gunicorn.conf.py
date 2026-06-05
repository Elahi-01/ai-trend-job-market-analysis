"""Gunicorn production configuration."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"