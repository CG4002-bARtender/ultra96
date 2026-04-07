"""
AudioServer: MQTT client that receives raw audio chunks from bar ESP32, buffers into clips,
"""

import os
import tempfile
import threading
import time
import wave

import numpy as np

from src.runner import DpuRunner

import librosa
import scipy.io.wavfile as wavfile

TARGET_SR      = 8000
TARGET_SAMPLES = 16000
N_FFT          = 256
HOP_LENGTH     = 128
N_MELS         = 40
FMIN           = 0
FMAX           = 4000

def load_wav_as_mel(path):
    sr, data = wavfile.read(path)
    if data.ndim > 1:
        data = data[:, 0]
    data = data.astype(np.float32)
    if sr != TARGET_SR:
        data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
    if len(data) < TARGET_SAMPLES:
        data = np.pad(data, (0, TARGET_SAMPLES - len(data)))
    else:
        data = data[:TARGET_SAMPLES]
    data = data.astype(np.int16)
    y = data.astype(np.float32) / 32768.0
    S = librosa.feature.melspectrogram(
        y=y, sr=TARGET_SR, n_fft=N_FFT, hop_length=HOP_LENGTH,
        n_mels=N_MELS, fmin=FMIN, fmax=FMAX,
    )
    return np.log(S + 1e-6).flatten().astype(np.float32)

# Audio config
SAMPLE_RATE    = 8000
SAMPLE_WIDTH   = 2      # int16 = 2 bytes
CHANNELS       = 1
IDLE_TIMEOUT_S = 1.5    # seconds of silence → clip complete

# MQTT topics 
TOPIC_AUDIO_IN = "audio"
TOPIC_ORDER    = "order"   # game engine input — {"id": <int>}
TOPIC_ACK      = "ack"      # bar ESP32 ACK — 0x01 byte


class AudioServer:
    def __init__(self, mqtt_client, dpu_runner: DpuRunner):
        self._mqtt   = mqtt_client
        self._runner = dpu_runner

        self._lock            = threading.Lock()
        self._chunks: list[bytes] = []
        self._total_bytes     = 0
        self._last_rx: float | None = None
        self._recording       = False

        # Background thread watches for idle timeout
        threading.Thread(target=self._timeout_watcher, daemon=True).start()
        print("[AudioServer] Ready — waiting for audio chunks on ultra96/audio_in")

    def on_audio_chunk(self, payload: bytes) -> None:
        """Called from MQTT on_message when topic == ultra96/audio_in."""
        if not payload:
            return

        with self._lock:
            if not self._recording:
                self._chunks.clear()
                self._total_bytes = 0
                self._recording = True
                print("[AudioServer] Recording started")

            self._chunks.append(payload)
            self._total_bytes += len(payload)
            self._last_rx = time.monotonic()
            print(f"\r[AudioServer] buffering… {self._total_bytes / 1024:.1f} kB", end="", flush=True)

    def _timeout_watcher(self) -> None:
        while True:
            time.sleep(0.25)
            clip = None
            with self._lock:
                if (self._recording
                        and self._last_rx is not None
                        and time.monotonic() - self._last_rx >= IDLE_TIMEOUT_S):
                    clip = b"".join(self._chunks)
                    self._chunks.clear()
                    self._total_bytes = 0
                    self._last_rx     = None
                    self._recording   = False

            if clip is not None:
                print() 
                self._process_clip(clip)

    def _process_clip(self, pcm: bytes) -> None:
        """Wrap raw PCM in a WAV, write to temp file, run inference, publish."""
        print(f"[AudioServer] Clip complete — {len(pcm) / 1024:.1f} kB, running inference...")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(pcm)

        try:
            mel = load_wav_as_mel(tmp_path)
            predicted, logits = self._runner.run(mel)

   
            drink_id = int(np.argmax(logits))

            # Publish to game engine
            self._mqtt.publish(TOPIC_ORDER, bytes([drink_id]))
            print(f"[AudioServer] Published → /order  {drink_id} ({predicted})")

            # ACK bar ESP32 — inference done, recording cycle complete
            self._mqtt.publish(TOPIC_ACK, b"\x01")
            print(f"[AudioServer] Sent ACK to bar ESP32")

        except Exception as e:
            print(f"[AudioServer] Inference failed: {e}")
            # NACK so bar ESP32 doesn't hang in WAITING_ACK
            self._mqtt.publish(TOPIC_ACK, b"\x00")
            print(f"[AudioServer] Sent NACK to bar ESP32")
        finally:
            os.unlink(tmp_path)
