import logging

def setup_global_logger() -> None:
    global logger
    logger = logging.getLogger('main')
    logger.setLevel(logging.INFO)
        
    # Check if the 'main' logger already has handlers
    if not logger.hasHandlers():
        # Create and set up the file handler
        file_handler = logging.FileHandler('git_org_repo.log')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        # Add the handler to the 'main' logger
        logger.addHandler(file_handler)

    # Disable propagation to the root logger
    logger.propagate = False

def get_global_logger() -> logging.Logger:
    return logger