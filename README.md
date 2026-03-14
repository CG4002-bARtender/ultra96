# Ultra96 MNIST DPU Inference Server

This project runs a hardware-accelerated MNIST digit classifier on an Ultra96 FPGA board using the Xilinx DPU (Deep Processing Unit). It listens for inference requests over MQTT, runs the model on the DPU, and publishes predictions back.

## What it does

- Loads an MNIST classifier (`.xmodel`) onto the DPU hardware accelerator
- Subscribes to the MQTT topic `ultra96/input` for incoming image payloads
- Runs inference on the DPU and publishes the predicted digit to `visualizer/event`

## Folder structure

```
.
├── main.py              # Entry point — wires together DpuRunner and Server
├── test.py              # Manual test client: sends a synthetic image and prints the prediction
├── src/
│   ├── runner.py        # DpuRunner: loads the DPU overlay and executes inference
│   ├── server.py        # Server: MQTT message handling and inference orchestration
│   └── comms.py         # MQTTClient: connection, pub/sub, reconnect logic
├── models/
│   └── mnist_classifier.xmodel   # Compiled DPU model
└── certs/
    └── ca.crt           # CA certificate (used if TLS is re-enabled)
```

## Program flow

1. `main.py` creates a `DpuRunner` (loads the bitstream and DPU model) and a `Server`
2. `Server` connects to the local MQTT broker and calls `loop_forever()`
3. On each message to `ultra96/input`, the server parses the JSON payload, reshapes the input array, and calls `DpuRunner.run()`
4. The DPU returns output logits; `argmax` picks the predicted digit
5. The result is published as JSON to `visualizer/event`

## Getting started

### Prerequisites

- Mosquitto running on localhost port 1883:
  ```bash
  mosquitto &
  # or, if already running as a service:
  sudo systemctl start mosquitto
  ```

### Running the server

```bash
sudo ./main.py
```

The server will load the DPU overlay (takes a few seconds) and then block waiting for MQTT messages.

### Running the test client

`test.py` sends a synthetic 28x28 image (a vertical line — representative of the digit "1") to the running server and prints the predicted digit.

In a second terminal:

```bash
sudo ./test.py
```

Expected output:
```
[test] Sent input to ultra96/input
[test] Response: {'source': 'ultra96', 'event_id': 1, 'from_device': 'test_client', 'prediction': 1}
[test] Predicted digit: 1
```

### Sending a custom input via MQTT

You can also publish directly using `mosquitto_pub`:

```bash
mosquitto_pub -t ultra96/input -m '{"dev":"my_device","input":[...]}'
```

The `input` field should be a flattened array of 784 int8 values (28x28 image).

Subscribe to results:

```bash
mosquitto_sub -t visualizer/event
```
