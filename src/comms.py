import time
import paho.mqtt.client as mqtt


class MQTTClient:
    def __init__(self, broker, port, on_message_cb):
        self._broker = broker
        self._port = port
        self._intentional_disconnect = False

        self._client = mqtt.Client(client_id="ultra96")
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = on_message_cb

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe("ultra96/audio_in")
            print("[MQTT] Subscribed to ultra96/audio_in")
        else:
            print(f"[MQTT] Connection failed (rc={rc})")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        if self._intentional_disconnect:
            return
        delay = 1
        while not self._intentional_disconnect:
            try:
                self._client.reconnect()
                return
            except Exception as e:
                print(f"[MQTT] Reconnect failed: {e}, retrying in {delay}s")
                time.sleep(delay)
                delay = min(delay * 2, 30)

    def connect(self):
        self._client.connect(self._broker, self._port, keepalive=60)

    def publish(self, topic, payload):
        self._client.publish(topic, payload)

    def loop_forever(self):
        self._client.loop_forever()

    def disconnect(self):
        self._intentional_disconnect = True
        self._client.disconnect()
