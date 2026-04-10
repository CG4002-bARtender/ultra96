"""
Minimal MQTT connectivity test — no DPU runner required.

Usage:
    python test_mqtt.py [broker] [port]

Defaults to localhost:1883.  Publishes a ping to 'test/ping' and expects
the broker to echo it back (requires the broker to be running; a loopback
subscribe/publish is used so no external subscriber is needed).

Exit codes:
    0 — connected and round-trip message confirmed
    1 — connection or message failure
"""

import sys
import threading
import time
import paho.mqtt.client as mqtt

BROKER  = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT    = int(sys.argv[2]) if len(sys.argv) > 2 else 1883
TOPIC   = "test/ping"
PAYLOAD = b"hello"
TIMEOUT = 5  # seconds to wait for round-trip

_received = threading.Event()
_connect_ok = threading.Event()
_connect_rc = [None]


def on_connect(client, userdata, connect_flags, reason_code, properties):
    _connect_rc[0] = reason_code
    if not reason_code.is_failure:
        print(f"[OK] Connected to {BROKER}:{PORT}")
        client.subscribe(TOPIC)
        _connect_ok.set()
    else:
        print(f"[FAIL] Connection refused: {reason_code}")
        _connect_ok.set()  # unblock main thread so it can exit


def on_subscribe(client, userdata, mid, reason_code_list, properties):
    print(f"[OK] Subscribed to '{TOPIC}'")
    client.publish(TOPIC, PAYLOAD)
    print(f"[..] Published ping to '{TOPIC}'")


def on_message(client, userdata, msg, properties=None):
    if msg.topic == TOPIC and msg.payload == PAYLOAD:
        print(f"[OK] Received echo on '{msg.topic}': {msg.payload}")
        _received.set()


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mqtt-test")
client.on_connect   = on_connect
client.on_subscribe = on_subscribe
client.on_message   = on_message

print(f"[..] Connecting to {BROKER}:{PORT} ...")
try:
    client.connect(BROKER, PORT, keepalive=10)
except OSError as e:
    print(f"[FAIL] Could not reach broker: {e}")
    sys.exit(1)

client.loop_start()

if not _connect_ok.wait(timeout=TIMEOUT):
    print(f"[FAIL] Timed out waiting for connection after {TIMEOUT}s")
    client.loop_stop()
    sys.exit(1)

if _connect_rc[0].is_failure:
    client.loop_stop()
    sys.exit(1)

if not _received.wait(timeout=TIMEOUT):
    print(f"[FAIL] Timed out waiting for echo message after {TIMEOUT}s")
    client.loop_stop()
    sys.exit(1)

print("[OK] MQTT broker is reachable and messaging works.")
client.disconnect()
client.loop_stop()
sys.exit(0)
