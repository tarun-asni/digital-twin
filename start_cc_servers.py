import subprocess
import time
import os
import sys
import signal
import threading

VENV_PYTHON = sys.executable

def run_provisioning_server():
    print("\n[1] Starting Provisioning Server (Flask)...")
    path = os.path.join(os.getcwd(), "Provisioning-server")
    return subprocess.Popen(
        [VENV_PYTHON, "run.py"],
        cwd=path,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        preexec_fn=os.setsid if os.name != "nt" else None
    )

def run_django_server():
    print("\n[2] Starting Django Server...")
    path = os.path.join(os.getcwd(), "command_center")
    return subprocess.Popen(
        [VENV_PYTHON, "manage.py", "runserver", "0.0.0.0:8000"],
        cwd=path,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        preexec_fn=os.setsid if os.name != "nt" else None
    )
    
def run_daphne_server():
    """Starts the Daphne ASGI server."""
    print("\n[3] Starting Daphne ASGI Server...")
    path = os.path.join(os.getcwd(), "command_center")
    return subprocess.Popen(
        [VENV_PYTHON, "-m", "daphne", "-b", "0.0.0.0", "-p", "8001", "sensegrid.asgi:application"],
        cwd=path,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        preexec_fn=os.setsid if os.name != "nt" else None
    )

def run_device_monitor():
    print("\n[4] Starting Device Monitor...")
    path = os.path.join(os.getcwd(), "command_center")
    return subprocess.Popen(
        [VENV_PYTHON, "manage.py", "start_device_monitor"],
        cwd=path,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        preexec_fn=os.setsid if os.name != "nt" else None
    )

def run_qcluster():
    print("\n[5] Starting Django QCluster...")
    path = os.path.join(os.getcwd(), "command_center")
    return subprocess.Popen(
        [VENV_PYTHON, "manage.py", "qcluster"],
        cwd=path,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        preexec_fn=os.setsid if os.name != "nt" else None
    )

if __name__ == "__main__":
    provisioning_process = run_provisioning_server()
    time.sleep(5)

    django_process = run_django_server()
    time.sleep(5)

    daphne_process = run_daphne_server()
    time.sleep(5)

    device_monitor_process = run_device_monitor()
    time.sleep(5)

    qcluster_process = run_qcluster()
    
    print("\n===== All services running =====")
    print("Press Ctrl+C to stop all...\n")

    # Background wait
    processes = [provisioning_process, django_process, daphne_process, device_monitor_process, qcluster_process]
    for p in processes:
        threading.Thread(target=p.wait, daemon=True).start()

    try:
        while True:
            time.sleep(1)  # Keep main thread alive
    except KeyboardInterrupt:
        print("\n\n===== Stopping all services... =====")
        for p in processes:
            try:
                if os.name == "nt":
                    p.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Failed to stop process {p.pid}: {e}")
