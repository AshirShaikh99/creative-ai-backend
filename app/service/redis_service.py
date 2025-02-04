import redis
import logging
import os
import time

logger = logging.getLogger(__name__)

class RedisService:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    config = {
                        'host': os.getenv('REDIS_HOST', 'localhost'),
                        'port': int(os.getenv('REDIS_PORT', 6379)),
                        'db': int(os.getenv('REDIS_DB', 0)),
                        'password': os.getenv('REDIS_PASSWORD'),
                        'decode_responses': True,
                        'socket_timeout': 5,
                        'retry_on_timeout': True,
                        'socket_connect_timeout': 5,
                        'health_check_interval': 30
                    }
                    
                    # Remove None values from config
                    config = {k: v for k, v in config.items() if v is not None}
                    
                    logger.info(f"Attempting to connect to Redis (attempt {attempt + 1}/{max_retries})")
                    cls._instance = redis.Redis(**config)
                    cls._instance.ping()  # Test the connection
                    logger.info(f"Redis connection established successfully to {config['host']}:{config['port']}")
                    break
                    
                except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"All attempts to connect to Redis failed. Last error: {str(e)}")
                        raise
                    logger.warning(f"Redis connection attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                except Exception as e:
                    logger.error(f"Unexpected error connecting to Redis: {str(e)}")
                    raise
                    
        return cls._instance

    @classmethod
    def set_value(cls, key: str, value: str, expire: int = 7200):
        """
        Set a value in Redis cache with expiration
        :param key: Cache key
        :param value: Value to cache
        :param expire: Expiration time in seconds (default 2 hours)
        :return: True if successful, False otherwise
        """
        try:
            redis_client = cls.get_instance()
            return redis_client.setex(name=key, time=expire, value=value)
        except Exception as e:
            logger.error(f"Error setting cache value: {str(e)}")
            return False

    @classmethod
    def get_value(cls, key: str):
        """
        Get a value from Redis cache
        :param key: Cache key
        :return: Cached value or None if not found
        """
        try:
            return cls.get_instance().get(key)
        except Exception as e:
            logger.error(f"Error getting cache value: {str(e)}")
            return None

    @classmethod
    def delete_value(cls, key: str):
        """
        Delete a value from Redis cache
        :param key: Cache key
        :return: True if successful, False otherwise
        """
        try:
            return bool(cls.get_instance().delete(key))
        except Exception as e:
            logger.error(f"Error deleting cache value: {str(e)}")
            return False