"""
dummy_audio_server.py — drop-in stand-in for the Ultra96 while the board is down.

Behaviour mirrors audio_server.py exactly, except instead of running DPU inference
it publishes a sequentially incrementing byte (0, 1, 2, ..., 255, 0, ...) to /order
so downstream components can be tested end-to-end.
"""

import threading
import time

import paho.mqtt.client as mqtt

# ── MQTT broker (edit to match your setup) ──────────────────────────────────
BROKER      = "localhost"
PORT        = 8883

# ── Topics (must match real audio_server.py) ────────────────────────────────
TOPIC_AUDIO_IN = "audio"
TOPIC_ORDER    = "order"
TOPIC_ACK      = "ack"

# ── Buffering config (mirrors audio_server.py) ──────────────────────────────
IDLE_TIMEOUT_S = 1.5   # seconds of silence → clip complete

# ── State ────────────────────────────────────────────────────────────────────
_lock        = threading.Lock()
_chunks: list[bytes] = []
_total_bytes = 0
_last_rx: float | None = None
_recording   = False
_counter     = 0        # increments each time a clip is processed
_mqtt_client: mqtt.Client | None = None


def _on_audio_chunk(payload: bytes) -> None:
    global _recording, _total_bytes, _last_rx

    if not payload:
        return

    with _lock:
        if not _recording:
            _chunks.clear()
            _total_bytes = 0
            _recording = True
            print("[DummyAudio] Recording started")

        _chunks.append(payload)
        _total_bytes += len(payload)
        _last_rx = time.monotonic()
        print(f"\r[DummyAudio] buffering… {_total_bytes / 1024:.1f} kB", end="", flush=True)


def _timeout_watcher() -> None:
    global _recording, _total_bytes, _last_rx

    while True:
        time.sleep(0.25)
        clip = None
        with _lock:
            if (_recording
                    and _last_rx is not None
                    and time.monotonic() - _last_rx >= IDLE_TIMEOUT_S):
                clip = b"".join(_chunks)
                _chunks.clear()
                _total_bytes = 0
                _last_rx = None
                _recording = False

        if clip is not None:
            print()
            _process_clip(clip)


def _process_clip(pcm: bytes) -> None:
    global _counter

    print(f"[DummyAudio] Clip complete — {len(pcm) / 1024:.1f} kB, skipping inference (dummy mode)")

    drink_id = (_counter % 10) + 1
    _counter += 1

    if _mqtt_client is not None:
        _mqtt_client.publish(TOPIC_ORDER, bytes([drink_id]))
        print(f"[DummyAudio] Published → {TOPIC_ORDER}  {drink_id}")

        _mqtt_client.publish(TOPIC_ACK, b"\x01")
        print(f"[DummyAudio] Sent ACK")


def _on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(TOPIC_AUDIO_IN)
        print(f"[DummyAudio] Connected — subscribed to '{TOPIC_AUDIO_IN}'")
    else:
        print(f"[DummyAudio] Connection failed (rc={rc})")


def _on_message(client, userdata, msg):
    if msg.topic == TOPIC_AUDIO_IN:
        _on_audio_chunk(bytes(msg.payload))


def main():
    global _mqtt_client

    client = mqtt.Client(client_id="dummy_ultra96")
    client.on_connect = _on_connect
    client.on_message = _on_message

    _mqtt_client = client

    threading.Thread(target=_timeout_watcher, daemon=True).start()

    client.connect(BROKER, PORT, keepalive=60)
    print(f"[DummyAudio] Connecting to {BROKER}:{PORT} ...")
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
