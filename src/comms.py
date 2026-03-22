import paho.mqtt.client as mqtt


class MQTTClient:
    def __init__(self, broker, port, on_message_cb):
        self._broker = broker
        self._port = port

        self._client = mqtt.Client(client_id="ultra96")
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = on_message_cb

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe("audio")
            print("[MQTT] Subscribed to audio")
        else:
            print(f"[MQTT] Connection failed (rc={rc})")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        if rc != 0:
            print(f"[MQTT] Unexpected disconnect (rc={rc}), loop_forever will reconnect")

    def connect(self):
        self._client.connect(self._broker, self._port, keepalive=60)

    def publish(self, topic, payload):
        self._client.publish(topic, payload)

    def loop_forever(self):
        self._client.loop_forever(retry_first_connection=True)

    def disconnect(self):
        self._client.disconnect()
