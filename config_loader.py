import json
import sys

import logger_config

logger = logger_config.get_global_logger()

global_config = None

def load_config() -> dict:
    global global_config
    try:
        if global_config is None:
            with open('config.json', 'r') as file:
                global_config = json.load(file)
            return global_config
    except FileNotFoundError:
        logger.error("config.json file not found")
        sys.exit(1)

def get_config():
    if global_config is None:
        load_config()
    return global_config
