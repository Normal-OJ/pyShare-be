bind = '0.0.0.0:8080'
timeout = 60
# Log
loglevel = 'debug'
errorlog = 'logs/error.log'
accesslog = 'logs/access.log'
# Worker
workers = 1
worker_class = 'eventlet'
# Stat
# statsd_host = 'statsd-exporter:9125'
# statsd_prefix = 'pyshare-web'

