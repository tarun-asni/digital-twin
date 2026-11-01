import signal
import threading
import sys
import time

from device_configuration.device_status_service import device_status_service

from django.core.management.base import BaseCommand
from device_configuration.device_monitor_service import device_monitor_service
from device_configuration.alert_monitor import check_pending_alerts

from sensegrid.config import HOURLY_TASK_WAIT_TIME, HEARTBEAT_INTERVAL_MINUTES


class Command(BaseCommand):
    help = 'Start device status monitoring service'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shutdown_event = threading.Event()

    def run_hourly_task(self):
        """
        This method is executed in a separate thread and runs its task every hour.
        """
        while not self.shutdown_event.is_set():
            # Wait for n hours (n * 3600) or until shutdown is triggered
            self.shutdown_event.wait(HOURLY_TASK_WAIT_TIME * 60 * 60)
            
            self.stdout.write(self.style.SUCCESS('Executing the hourly task...'))
            check_pending_alerts()

    def check_device_heartbeats(self):
        """
        Checks all devices and updates their status to 'INACTIVE' if their
        heartbeat has not been updated in the last minute.
        """
        # Check heartbeats every minute
        while not self.shutdown_event.is_set():
            self.shutdown_event.wait(HEARTBEAT_INTERVAL_MINUTES * 60)
            
            updated_devices = device_status_service.check_heartbeats()
            self.stdout.write(self.style.SUCCESS(f'Checked heartbeats. Updated devices: {updated_devices}.'))
            self.stdout.write(self.style.SUCCESS(f'Updated devices count: {len(updated_devices)}'))

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting device status monitoring service...'))
        device_monitor_service.start_periodic_check()

        # Start the hourly task in a background thread
        hourly_thread = threading.Thread(target=self.run_hourly_task, daemon=True)
        hourly_thread.start()

        # Start the heartbeat check in a background thread
        heartbeat_thread = threading.Thread(target=self.check_device_heartbeats, daemon=True)
        heartbeat_thread.start()

        # Graceful shutdown handler
        def shutdown_handler(sig, frame):
            self.stdout.write(self.style.WARNING("\nStopping device status monitoring service..."))
            self.shutdown_event.set()  # Signal threads to stop
            device_monitor_service.stop()
            hourly_thread.join()  # Wait for the hourly thread to finish
            sys.exit(0)

        # Register signals for Ctrl+C and kill
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        self.stdout.write(self.style.SUCCESS('Services are running. Press Ctrl+C to stop.'))
        # Keep the main thread alive until a shutdown signal is received
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            shutdown_handler(None, None)
