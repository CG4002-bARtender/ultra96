"""
bARtender Ultra96 — Entry point
"""

from src.runner       import DpuRunner
from src.comms        import MQTTClient
from src.audio_server import AudioServer, TOPIC_AUDIO_IN

BROKER    = "localhost"
PORT      = 1883
XMODEL    = "models/drink_classifier.xmodel"


def main():
    print("[main] Loading DPU model...")
    runner = DpuRunner(XMODEL)
    print("[main] DPU model loaded")

    # on_message callback — route audio chunks to AudioServer
    # AudioServer is created after mqtt so it can hold a reference for publishing
    audio_server_ref: list[AudioServer] = []

    def on_message(client, userdata, msg):
        if msg.topic == TOPIC_AUDIO_IN and audio_server_ref:
            audio_server_ref[0].on_audio_chunk(bytes(msg.payload))

    mqtt = MQTTClient(BROKER, PORT, on_message_cb=on_message)
    mqtt.connect()

    audio_server = AudioServer(mqtt_client=mqtt, dpu_runner=runner)
    audio_server_ref.append(audio_server)

    print("[main] Listening for audio on ultra96/audio_in ...")
    mqtt.loop_forever()


if __name__ == "__main__":
    main()
