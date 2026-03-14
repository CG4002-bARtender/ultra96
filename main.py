#!/usr/local/share/pynq-venv/bin/python3
from src.runner import DpuRunner
from src.server import Server

XMODEL_PATH = "models/mnist_classifier.xmodel"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883


def main():
    runner = DpuRunner(XMODEL_PATH)
    server = Server(runner, MQTT_BROKER, MQTT_PORT)
    server.start()


if __name__ == "__main__":
    main()
