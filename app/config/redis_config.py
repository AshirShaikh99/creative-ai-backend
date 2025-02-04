import os


REDIS_CONFIG = {
    'host': os.environ.get('REDIS_HOST'),
    'port': int(os.environ.get('REDIS_PORT', 6379)),
    'password': os.environ.get('REDIS_PASSWORD'),
    'username': os.environ.get('REDIS_USERNAME', 'default'),
    'ssl': os.environ.get('REDIS_SSL', 'true').lower() == 'true',
    'decode_responses': True,
    'socket_timeout': 5,
    'retry_on_timeout': True,
    'max_connections': 10
}