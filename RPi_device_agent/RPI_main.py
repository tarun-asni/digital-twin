import os
import sys
import logging
import subprocess
from device_provisioning.Provisioning import Provisioning 
# Set working directory to script's root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR) # Current working directory is RPi_device_agent
DEVICE_TYPE = os.getenv("DEVICE_TYPE", "").upper()
def run_provisioning():
    print("\n=== Starting Device Provisioning ===\n")
    try:
        logging.basicConfig(level=logging.INFO)
        env = os.environ.copy()
        # Add the current directory (RPi_device_agent) to PYTHONPATH
        # so Python can find 'device_provisioning' as a package.
        env["PYTHONPATH"] = BASE_DIR + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [sys.executable, "-m", "device_provisioning.main"],
            capture_output=True,
            text=True,
            env=env 
        )

        print(result.stdout)
        if result.returncode != 0:
            print("\nProvisioning failed!\n")
            print(result.stderr)
            return False

        return True
    except Exception as e:
        print("\nProvisioning failed due to exception!\n")
        print(f"Error: {e}")
        return False

def run_camera_stream():
    print("\n=== Starting Camera Stream ===\n")
    try:
        # Get current working directory (RPi_device_agent)
        current_dir = os.path.abspath(os.path.dirname(__file__))

        # Add current dir to PYTHONPATH so camera_stream becomes importable
        env = os.environ.copy()
        env["PYTHONPATH"] = current_dir + os.pathsep + env.get("PYTHONPATH", "")

        # Run as a module: camera_stream.app
        subprocess.run(
            [sys.executable, "-m", "camera_stream.app"],
            check=True,
            env=env
        )
        return True
    except Exception as e:
        print("Camera stream failed to start.")
        print(f"Error: {e}")
        return False

def run_drone():
    print("\n=== Starting Drone Stream ===\n")
    try:
        # Get current working directory (RPi_device_agent)
        current_dir = os.path.abspath(os.path.dirname(__file__))

        # Add current dir to PYTHONPATH so drone_flight becomes importable
        env = os.environ.copy()
        env["PYTHONPATH"] = current_dir + os.pathsep + env.get("PYTHONPATH", "")

        # Run as a module: drone_flight.app
        subprocess.run(
            [sys.executable, "-m", "drone_flight.drone"],
            check=True,
            env=env
        )
        return True
    except Exception as e:
        print("drone failed to start.")
        print(f"Error: {e}")
        return False

def run_sensor():
    print("\n=== Starting Sensor  ===\n")
    try:
        # Get current working directory (RPi_device_agent)
        current_dir = os.path.abspath(os.path.dirname(__file__))

        # Add current dir to PYTHONPATH so sensor becomes importable
        env = os.environ.copy()
        env["PYTHONPATH"] = current_dir + os.pathsep + env.get("PYTHONPATH", "")

        # Run as a module: sensor.app
        subprocess.run(
            [sys.executable, "-m", "sensor.multi_sensor_dynamic"],
            check=True,
            env=env
        )
        return True
    except Exception as e:
        print("sensor failed to start.")
        print(f"Error: {e}")
        return False


def main():
    provision_instance = Provisioning()
    success = run_provisioning()
    if success:
        provision_instance.start_heartbeat_scheduler()
        if DEVICE_TYPE == "CAMERA":
            run_camera_stream()
        if DEVICE_TYPE == "SENSOR":
            run_sensor()
        if DEVICE_TYPE == "DRONE":
            run_drone()
    else:
        print("Exiting script due to provisioning failure.")

if __name__ == "__main__":
    main()