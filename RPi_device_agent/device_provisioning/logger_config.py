import logging
import sys

# Setup logger only if not already set
if not logging.getLogger().hasHandlers():
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Or DEBUG, WARNING

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler('app.log', mode='a')
    file_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
