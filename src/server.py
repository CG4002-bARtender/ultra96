import json

import numpy as np

from src.comms import MQTTClient
from src.runner import DpuRunner

TOPIC_INPUT = "ultra96/input"
TOPIC_OUTPUT = "visualizer/event"


class Server:
    def __init__(self, runner: DpuRunner, mqtt_broker, mqtt_port):
        self._runner = runner
        self._event_count = 0
        self._client = MQTTClient(mqtt_broker, mqtt_port, self._on_message)

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except Exception as e:
            print(f"[Server] Failed to parse message: {e}")
            return

        device_id = data.get("dev", data.get("device_id", "unknown"))
        self._event_count += 1

        input_shape = tuple(self._runner.input_tensors[0].dims)
        raw = data.get("input")
        if raw is not None:
            input_array = np.array(raw, dtype=np.int8).reshape(input_shape)
        else:
            input_array = np.zeros(input_shape, dtype=np.int8)

        output = self._runner.run(input_array)
        prediction = int(np.argmax(output))

        event = {
            "source": "ultra96",
            "event_id": self._event_count,
            "from_device": device_id,
            "prediction": prediction,
        }
        self._client.publish(TOPIC_OUTPUT, json.dumps(event, separators=(',', ':')))

    def start(self):
        try:
            self._client.connect()
            self._client.loop_forever()
        except KeyboardInterrupt:
            print(f"\n[Server] Shutting down. Events processed: {self._event_count}")
        finally:
            self._client.disconnect()
