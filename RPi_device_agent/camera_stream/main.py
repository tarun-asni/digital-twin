import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from command_center.ai_task.zone_monitor import select_restricted_zone
from command_center.ai_task.detection_utils import run_detection

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    zone = select_restricted_zone()

    if not zone:
        logger.warning("No restricted zone selected. Proceeding without zone monitoring.")
    
    run_detection(zone)

if __name__ == "__main__":
    main()
