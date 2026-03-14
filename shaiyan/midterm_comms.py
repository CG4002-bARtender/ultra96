import paho.mqtt.client as mqtt
import ssl
import json
import time
import random
from pathlib import Path

MQTT_BROKER = "localhost"
MQTT_PORT = 8883

TOPIC_INPUT  = "ultra96/input"
TOPIC_OUTPUT = "visualizer/event"

GESTURES = ["grab", "pour", "shake", "stir", "idle"]
DRINKS   = ["mojito", "margarita", "old_fashioned", "cosmopolitan", "gin_tonic"]
ACTIONS  = ["pour_spirit", "add_mixer", "muddle", "shake_cocktail", "garnish", "serve"]

G = "\033[92m"; M = "\033[95m"; Y = "\033[93m"
R = "\033[91m"; B = "\033[94m"; C = "\033[96m"
D = "\033[2m"; X = "\033[0m"; BOLD = "\033[1m"

_intentional_disconnect = False
event_count = 0


def setup_tls(client):
    certs_dir = Path(__file__).resolve().parent / "certs"
    ca_cert = str(certs_dir / "ca.crt")
    if not Path(ca_cert).exists():
        raise FileNotFoundError(f"Missing: {ca_cert}")
    client.tls_set(ca_certs=ca_cert, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.tls_insecure_set(True)
    print(f"{G}[TLS] CA cert loaded{X}")


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"{G}[Ultra96] Connected to broker (TLS){X}")
        client.subscribe(TOPIC_INPUT)
    else:
        print(f"{R}[Ultra96] Connection failed (rc={rc}){X}")


def on_disconnect(client, userdata, rc, properties=None):
    global _intentional_disconnect
    if _intentional_disconnect:
        return
    print(f"{R}[Ultra96] Disconnected (rc={rc}). Reconnecting...{X}")
    delay = 1
    while not _intentional_disconnect:
        try:
            client.reconnect()
            print(f"{G}[Ultra96] Reconnected!{X}")
            return
        except Exception as e:
            print(f"{R}[Ultra96] Retry in {delay}s... ({e}){X}")
            time.sleep(delay)
            delay = min(delay * 2, 30)


def on_message(client, userdata, msg):
    global event_count

    try:
        data = json.loads(msg.payload.decode())
    except Exception as e:
        print(f"{R}[Ultra96] Parse failed: {e}{X}")
        return

    device_id = data.get("dev", data.get("device_id", "unknown"))
    msg_id = data.get("id", data.get("msg_id", "?"))
    event_count += 1

    print()
    print(f"{C}{BOLD}[RECV ← ultra96/input]{X} from {B}{device_id}{X}")
    print(f"  id:    {msg_id}")
    print(f"  size:  {len(msg.payload)} bytes")

    gesture = random.choice(GESTURES)
    gesture_conf = round(random.uniform(0.75, 0.99), 2)
    drink = random.choice(DRINKS) if gesture != "idle" else None
    drink_conf = round(random.uniform(0.80, 0.95), 2) if drink else None
    action = random.choice(ACTIONS) if drink else None

    event = {
        "source": "ultra96",
        "event_id": event_count,
        "from_device": device_id,
        "gesture": gesture,
        "gesture_confidence": gesture_conf,
    }
    if drink:
        event["drink"] = drink
        event["drink_confidence"] = drink_conf
    if action:
        event["action"] = action

    result_json = json.dumps(event, separators=(',', ':'))
    client.publish(TOPIC_OUTPUT, result_json)

    print(f"\n{M}{BOLD}[SENT → visualizer/event]{X}")
    print(f"  gesture: {gesture} ({gesture_conf})")
    if drink:
        print(f"  drink:   {drink} ({drink_conf})")
    if action:
        print(f"  action:  {action}")
    print(f"  size:    {len(result_json)} bytes")
    print(f"{D}{'-' * 50}{X}")


def main():
    global _intentional_disconnect

    client = mqtt.Client(client_id="ultra96")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    setup_tls(client)

    print(f"{'=' * 50}")
    print(f"  ULTRA96 — bARtender AI Pipeline")
    print(f"{'=' * 50}")
    print(f"  Broker:  {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Sub:     {TOPIC_INPUT}")
    print(f"  Pub:     {TOPIC_OUTPUT}")
    print(f"{'=' * 50}")
    print()

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        print(f"{R}[ERROR] Cannot connect: {e}{X}")
        print(f"{Y}  Is the SSH tunnel running?{X}")
        return

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        _intentional_disconnect = True
        print(f"\n{Y}[Ultra96] Done. Events: {event_count}{X}")
    finally:
        _intentional_disconnect = True
        client.disconnect()


if __name__ == "__main__":
    main()
