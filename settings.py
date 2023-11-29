import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='app.log',
                    filemode='a')

logger = logging.getLogger(__name__)

global_config = None

def load_config(crucial_keys) -> dict:
    global global_config
    try:
        if global_config is None:
            with open('config.json', 'r') as file:
                global_config = json.load(file)

            for key in crucial_keys:
                if key not in global_config:
                    raise ValueError(f"{key} not found in config.json, exiting now...")
            return global_config
    except FileNotFoundError:
        logger.error("config.json file not found")
        sys.exit(1)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

def get_config():
    crucial_keys = ['github_token', 'private_key_path']
    if global_config is None:
        load_config(crucial_keys)
    return global_config
