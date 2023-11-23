import json
import sys

import logger_config

logger = logger_config.get_global_logger()

def load_config() -> dict:
    try:
        global global_config
        with open('config.json', 'r') as file:
            global_config: dict = json.load(file)
        return global_config
    except FileNotFoundError:
        logger.error("config.json file not found")
        sys.exit(1)

def get_config():
    return global_config
