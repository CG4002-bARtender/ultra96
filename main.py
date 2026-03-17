import sys
import numpy as np
import scipy.io.wavfile as wavfile
import librosa

from src.runner import DpuRunner, CLASSES

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


def run(runner: DpuRunner, wav_path: str):
    print(f"[DEBUG] run() called with wav_path={wav_path}")
    print(f"Loading {wav_path} ...")
    mel = load_wav_as_mel(wav_path)
    print(f"Mel shape: (40, {len(mel) // 40})  —  running DPU inference ...")

    predicted, logits = runner.run(mel)

    e = np.exp(logits - logits.max())
    probs = e / e.sum()

    print(f"\nPrediction: {predicted}\n")
    print(f"{'Class':<16} {'Logit':>6}  {'Prob':>7}")
    print("-" * 34)
    for cls, logit, prob in sorted(zip(CLASSES, logits, probs),
                                    key=lambda x: -x[2]):
        marker = " <--" if cls == predicted else ""
        print(f"{cls:<16} {logit:>6.1f}  {prob:>6.2%}{marker}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <wav_file>")
        sys.exit(1)
    wav_path = sys.argv[1]
    print(f"[DEBUG] __main__ reached, wav_path={wav_path}")
    print(f"[DEBUG] loading DpuRunner ...")
    runner = DpuRunner("models/drink_classifier.xmodel")
    print(f"[DEBUG] DpuRunner loaded OK")
    run(runner, wav_path)
