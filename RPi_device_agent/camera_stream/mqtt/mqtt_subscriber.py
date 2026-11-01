import os
import ssl
import logging
import threading
import paho.mqtt.client as mqtt

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Get the absolute path to the project root
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]

CERTS_DIR = PROJECT_ROOT / "RPi_device_agent" / "client_certs"

DEVICE_ID = os.getenv("DEVICE_ID")
CA_CERT = CERTS_DIR / "rootCA.pem"
DEVICE_CERT = CERTS_DIR / f"{DEVICE_ID}_cert.pem"
DEVICE_KEY = CERTS_DIR / f"{DEVICE_ID}_cert_key.pem"


class MqttSubscriber:
    def __init__(self):
        self.client = mqtt.Client(client_id=DEVICE_ID, clean_session=False)
        self.client.on_connect = self.on_connect
        self.topic_callbacks = {}  # Dict to hold topic → callback mapping
        self.client.on_message = self.dispatch_message

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"[MQTT] Connected to broker with result code {rc}")
        for topic in self.topic_callbacks.keys():
            client.subscribe(topic, qos=2)
            logger.info(f"[MQTT] Subscribed to topic: {topic}")

    def dispatch_message(self, client, userdata, msg):
        logger.info(f"[MQTT] Message received on {msg.topic}")
        if msg.topic in self.topic_callbacks:
            logger.info(f"[MQTT] Dispatching message to callback for topic: {msg.topic}")
            callback = self.topic_callbacks[msg.topic]
            callback(msg)
        else:
            logger.warning(f"[MQTT] No callback registered for topic: {msg.topic}")

    def register_topic(self, topic, callback):
        self.topic_callbacks[topic] = callback

    def start(self):
        thread = threading.Thread(target=self._run)
        thread.daemon = True
        thread.start()

    def _run(self):
        try:
            self.client.tls_set(ca_certs=CA_CERT,
                       certfile=DEVICE_CERT,
                       keyfile=DEVICE_KEY,
                       tls_version=ssl.PROTOCOL_TLSv1_2)
            self.client.connect(os.getenv("MQTT_HOST"), int(os.getenv("MQTT_PORT", 8883)), 60)
        except Exception as e:
            logger.error(f"MQTT TLS connection failed: {e}")
            return

        self.client.loop_forever()
