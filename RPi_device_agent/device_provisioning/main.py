import os
import sys
import logging

from . import logger_config
from .Provisioning import Provisioning

logger = logging.getLogger(__name__)


def main():
    provision = Provisioning()
    logger.info("start_provision called")
    success = provision.start_provision()
    if success:
        sys.exit(0) 
    else:
        logger.error("Provisioning failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()