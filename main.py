from src.runner       import DpuRunner
from src.comms        import MQTTClient
from src.audio_server import AudioServer, TOPIC_AUDIO_IN

BROKER  = "localhost"
PORT    = 8883
XMODEL  = "models/model2.xmodel"


CA_CERT     = "certs/ca.crt"
CLIENT_CERT = "certs/ultra96.crt"
CLIENT_KEY  = "certs/ultra96.key"


def main():
    print("[main] Loading DPU model...")
    runner = DpuRunner(XMODEL)
    print("[main] DPU model loaded")

    try:
        audio_server_ref: list[AudioServer] = []

        def on_message(client, userdata, msg):
            if msg.topic == TOPIC_AUDIO_IN and audio_server_ref:
                audio_server_ref[0].on_audio_chunk(bytes(msg.payload))

        mqtt = MQTTClient(BROKER, PORT, on_message_cb=on_message,
                          ca_cert=CA_CERT,
                          client_cert=CLIENT_CERT,
                          client_key=CLIENT_KEY)
        mqtt.connect()

        audio_server = AudioServer(mqtt_client=mqtt, dpu_runner=runner)
        audio_server_ref.append(audio_server)

        print("[main] Listening for audio on ultra96/audio_in ...")
        mqtt.loop_forever()
    except KeyboardInterrupt:
        print("[main] Interrupted — shutting down")
    finally:
        # Release vart.Runner before DpuOverlay so XRT drops DPU_0 context cleanly.
        runner.close()


if __name__ == "__main__":
    main()
