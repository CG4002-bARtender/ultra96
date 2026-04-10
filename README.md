# Ultra96 Drink Classifier — Audio DPU Inference Server

This project runs a hardware-accelerated drink classifier on an Ultra96 FPGA board using the Xilinx DPU (Deep Processing Unit). It listens for raw PCM audio chunks over MQTT (sent by a bar ESP32), buffers them into clips, extracts mel spectrograms, and runs inference on the DPU to identify the drink being poured. Results are published back to a game engine and an ACK is sent to the ESP32.

## What it does

- Loads a drink classifier (`.xmodel`) onto the DPU hardware accelerator
- Subscribes to MQTT topic `audio` for raw PCM audio chunks from the bar ESP32
- Buffers chunks until 1.5 s of silence, then treats the buffer as a complete clip
- Converts the clip to a WAV file, extracts a 40-band mel spectrogram via librosa
- Quantizes the spectrogram to int8 and runs DPU inference
- Publishes the predicted drink ID (1 byte) to `order` (game engine input)
- Publishes `0x01` ACK or `0x00` NACK to `ack` (bar ESP32 feedback)

### Drink classes

`aviation`, `godfather`, `irishcoffee`, `martini`, `midorisour`, `oldfashioned`, `scotchneat`, `tuxedo`, `vodkaneat`, `whiskeyneat`

## Folder structure

```
.
├── main.py                        # Entry point — wires DpuRunner, MQTTClient, AudioServer
├── src/
│   ├── runner.py                  # DpuRunner: loads the DPU overlay and executes inference
│   ├── audio_server.py            # AudioServer: buffers audio chunks, extracts mel, orchestrates inference
│   ├── comms.py                   # MQTTClient: mTLS connection, pub/sub, auto-reconnect
│   ├── server.py                  # Standalone WAV inference utility (scipy-only, no librosa)
│   └── __init__.py
├── models/
│   └── drink_classifier.xmodel   # Compiled DPU model
└── certs/
    ├── ca.crt                     # CA certificate
    ├── ultra96.crt                # Client certificate
    └── ultra96.key                # Client private key
```

## MQTT topics

| Topic   | Direction | Payload                           | Consumer         |
|---------|-----------|-----------------------------------|------------------|
| `audio` | inbound   | Raw PCM bytes (int16, 8 kHz mono) | Ultra96          |
| `order` | outbound  | 1 byte — predicted drink index    | Game engine      |
| `ack`   | outbound  | `0x01` ACK / `0x00` NACK          | Bar ESP32        |

## Program flow

1. `main.py` creates a `DpuRunner` (loads `dpu.bit` bitstream + `drink_classifier.xmodel`)
2. `MQTTClient` connects to `localhost:8883` with mTLS (CA cert + client cert/key)
3. `AudioServer` starts a background timeout-watcher thread
4. On each `audio` message, `AudioServer.on_audio_chunk()` appends the PCM payload to a buffer
5. After 1.5 s of silence the buffer is wrapped into a temporary WAV file
6. `load_wav_as_mel()` resamples to 8 kHz, extracts a 40-band log-mel spectrogram with librosa, and returns a flat float32 array
7. `DpuRunner.run()` reads the fix-point scale from the model, quantizes the mel to int8, and runs `execute_async` on the DPU
8. `argmax` of the output logits selects the predicted drink class
9. The drink index is published to `order`; ACK/NACK is published to `ack`; the temp file is deleted

## Getting started

### Prerequisites

- Mosquitto broker running with mTLS on port 8883
- Client certificates in `certs/` (`ca.crt`, `ultra96.crt`, `ultra96.key`)
- Python packages: `pynq_dpu`, `paho-mqtt`, `librosa`, `scipy`, `numpy`

### Running the server

```bash
pynq-python main.py
```

The server loads the DPU overlay (takes a few seconds), then blocks waiting for MQTT audio messages.

> **Note:** must be run with `pynq-python`, not plain `python3`, as it sets up the environment variables required by XRT/VART.

### Testing with a WAV file (standalone)

`src/server.py` is a scipy-based WAV inference utility that can run a single file through the DPU without the MQTT stack:

```python
from src.runner import DpuRunner
from src.server import run

runner = DpuRunner("models/drink_classifier.xmodel")
run(runner, "path/to/clip.wav")
```

It prints the predicted class and a ranked probability table.

### Sending raw audio via MQTT

The bar ESP32 sends raw int16 PCM at 8 kHz mono. You can simulate it with:

```bash
# Send a raw PCM chunk
mosquitto_pub -t audio -f clip.raw

# Watch the predicted drink order
mosquitto_sub -t order

# Watch ACKs
mosquitto_sub -t ack
```
