#!/usr/local/share/pynq-venv/bin/python3
"""
Sends a synthetic MNIST input (vertical line = digit "1") to the running
server via MQTT and prints the prediction it returns.
"""
import json
import sys
import threading

import numpy as np
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_INPUT = "ultra96/input"
TOPIC_OUTPUT = "visualizer/event"

input_array = np.zeros((1, 28, 28, 1), dtype=np.int8)
for i in range(28):
    input_array[0][i][14][0] = 127  # vertical line down the middle

_done = threading.Event()


def on_connect(client, userdata, flags, rc, properties=None):
    if rc != 0:
        print(f"[test] Connection failed (rc={rc})")
        _done.set()
        return
    client.subscribe(TOPIC_OUTPUT)
    payload = json.dumps({
        "dev": "test_client",
        "input": input_array.flatten().tolist(),
    }, separators=(',', ':'))
    client.publish(TOPIC_INPUT, payload)
    print(f"[test] Sent input to {TOPIC_INPUT}")


def on_message(client, userdata, msg):
    result = json.loads(msg.payload.decode())
    print(f"[test] Response: {result}")
    print(f"[test] Predicted digit: {result.get('prediction')}")
    _done.set()


client = mqtt.Client(client_id="test_client")
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=10)
except Exception as e:
    print(f"[test] Could not connect to broker: {e}")
    sys.exit(1)

client.loop_start()
if not _done.wait(timeout=10):
    print("[test] Timed out waiting for response")
    sys.exit(1)
client.loop_stop()
client.disconnect()
