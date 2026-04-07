"""
Sends a WAV file to the local AudioServer via MQTT (mTLS).
Streams the PCM in ~32 ms chunks to simulate the ESP32, then waits for the
server's idle timeout to fire inference.

Run this on the Ultra96 itself — broker is localhost.

Usage:
    python test_pub.py [wavfile]
    python test_pub.py aviation00.wav
Default: aviation00.wav
"""
import ssl
import sys
import threading
import time
import wave

import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT   = 8883

CA_CERT     = "certs/ca.crt"
CLIENT_CERT = "certs/ultra96.crt"
CLIENT_KEY  = "certs/ultra96.key"

TOPIC_AUDIO = "audio"
TOPIC_ORDER = "order"
TOPIC_ACK   = "ack"

# Match ESP32 chunk size: 512 bytes = 256 int16 samples = ~32 ms at 8 kHz
CHUNK_BYTES = 512

WAV_FILE = sys.argv[1] if len(sys.argv) > 1 else "old_fashioned_slow_3_b2.wav"

with wave.open(WAV_FILE, "rb") as wf:
    sample_rate = wf.getframerate()
    pcm_data    = wf.readframes(wf.getnframes())
    print(f"[test] Loaded '{WAV_FILE}': {wf.getnchannels()}ch, "
          f"{sample_rate} Hz, {len(pcm_data)} bytes")

# How long each chunk represents in real time (for pacing)
CHUNK_DURATION_S = CHUNK_BYTES / (sample_rate * 2)  # 2 bytes per int16 sample

_done = threading.Event()


def stream_audio(client):
    """Send PCM in chunks at roughly real-time pace, mimicking the ESP32."""
    total = len(pcm_data)
    sent  = 0
    chunk_num = 0
    while sent < total:
        chunk = pcm_data[sent:sent + CHUNK_BYTES]
        client.publish(TOPIC_AUDIO, chunk)
        sent      += len(chunk)
        chunk_num += 1
        time.sleep(CHUNK_DURATION_S)

    print(f"[test] Streamed {chunk_num} chunks ({sent} bytes) → '{TOPIC_AUDIO}'")
    print("[test] Waiting for idle timeout + inference…")


def on_connect(client, userdata, flags, rc, properties=None):
    if rc != 0:
        print(f"[test] Connection failed (rc={rc})")
        _done.set()
        return
    client.subscribe(TOPIC_ORDER)
    client.subscribe(TOPIC_ACK)
    # Stream in a background thread so the MQTT loop stays unblocked
    threading.Thread(target=stream_audio, args=(client,), daemon=True).start()


def on_message(client, userdata, msg):
    if msg.topic == TOPIC_ORDER:
        if len(msg.payload) >= 1:
            print(f"[test] Order → drink_id: {msg.payload[0]}")
    elif msg.topic == TOPIC_ACK:
        status = "OK" if msg.payload == b"\x01" else "NACK"
        print(f"[test] ACK: {status}")
        _done.set()


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="test_client",
)
client.tls_set(
    ca_certs=CA_CERT,
    certfile=CLIENT_CERT,
    keyfile=CLIENT_KEY,
    tls_version=ssl.PROTOCOL_TLS_CLIENT,
)
client.on_connect = on_connect
client.on_message = on_message

print(f"[test] Connecting to {MQTT_BROKER}:{MQTT_PORT} …")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=10)
except Exception as e:
    print(f"[test] Could not connect: {e}")
    sys.exit(1)

client.loop_start()
# timeout = audio duration + 1.5 s idle + inference headroom
timeout = (len(pcm_data) / (sample_rate * 2)) + 1.5 + 10
if not _done.wait(timeout=timeout):
    print("[test] Timed out waiting for response")
    sys.exit(1)
client.loop_stop()
client.disconnect()
