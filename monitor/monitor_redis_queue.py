import redis
import time
import os
import logging

# --- Logging Setup ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format='%(asctime)s - %(levelname)s - %(message)s')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
QUEUE_NAME_PREFIX = os.getenv('QUEUE_NAME_PREFIX', 'bull') # BullMQ default prefix
QUEUE_NAME = os.getenv('QUEUE_NAME', 'jobs')
POLL_INTERVAL_SECONDS = int(os.getenv('POLL_INTERVAL_SECONDS', 5))

def get_redis_connection():
    """Establishes a connection to Redis."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
        r.ping()
        logging.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        return r
    except redis.exceptions.ConnectionError as e:
        logging.error(f"Error connecting to Redis: {e}")
        return None

def get_queue_length(r_conn, queue_name_prefix, queue_name):
    """Gets the length of the specified BullMQ queue."""
    key_to_check = f"{queue_name_prefix}:{queue_name}:wait"
    try:
        length = r_conn.llen(key_to_check)
        if length is None:
            key_to_check_legacy = f"{queue_name_prefix}:{queue_name}"
            length = r_conn.llen(key_to_check_legacy)
            if length is not None:
                logging.debug(f"Using legacy key pattern '{key_to_check_legacy}' for queue length.")
                key_to_check = key_to_check_legacy
            else:
                key_to_check_v4 = f"{queue_name_prefix}:{queue_name}:waiting"
                length = r_conn.llen(key_to_check_v4)
                if length is not None:
                    logging.debug(f"Using BullMQ v4+ key pattern '{key_to_check_v4}' for queue length.")
                    key_to_check = key_to_check_v4
                else:
                    logging.warning(f"Key '{key_to_check}', '{key_to_check_legacy}', or '{key_to_check_v4}' not found or not a list. Assuming length 0.")
                    return 0
        return length
    except redis.exceptions.ResponseError as e:
        logging.error(f"Redis error when checking length of '{key_to_check}': {e}. Assuming length 0.")
        return 0
    except Exception as e:
        logging.error(f"Unexpected error when checking length of '{key_to_check}': {e}. Assuming length 0.")
        return 0


if __name__ == "__main__":
    redis_conn = get_redis_connection()
    if redis_conn:
        logging.info(f"Monitoring Redis queue '{QUEUE_NAME_PREFIX}:{QUEUE_NAME}' every {POLL_INTERVAL_SECONDS} seconds...")
        last_known_length = None  # Track queue length changes for event-driven logging
        try:
            while True:
                length = get_queue_length(redis_conn, QUEUE_NAME_PREFIX, QUEUE_NAME)

                # Event-driven logging: only log when queue has items or length changes
                if length > 0:
                    logging.info(f"Queue '{QUEUE_NAME_PREFIX}:{QUEUE_NAME}' length: {length}")
                elif last_known_length is not None and last_known_length > 0 and length == 0:
                    # Log when queue drains to zero (transition event)
                    logging.info(f"Queue '{QUEUE_NAME_PREFIX}:{QUEUE_NAME}' drained to 0")

                last_known_length = length
                time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user.")
        finally:
            redis_conn.close()
            logging.info("Redis connection closed.")
