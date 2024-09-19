from config import db_config
import redis

redis_client = redis.Redis(
    host=db_config.REDIS_DB_HOST,
    port=db_config.REDIS_DB_PORT,
    db=db_config.REDIS_DB_NUM,
)
