import sys
import numpy as np
import scipy.io.wavfile
import scipy.signal

from src.runner import DpuRunner, CLASSES

TARGET_SR      = 8000
N_FFT          = 256
HOP_LENGTH     = 128
N_MELS         = 40
FMIN           = 0
FMAX           = 4000
TARGET_SAMPLES = 16000


def _mel_filterbank():
    def hz_to_mel(hz):
        return 2595.0 * np.log10(1.0 + hz / 700.0)
    def mel_to_hz(mel):
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    n_freqs = N_FFT // 2 + 1
    mel_points = np.linspace(hz_to_mel(FMIN), hz_to_mel(FMAX), N_MELS + 2)
    hz_points  = mel_to_hz(mel_points)
    bins = np.floor((N_FFT + 1) * hz_points / TARGET_SR).astype(int)

    fb = np.zeros((N_MELS, n_freqs))
    for m in range(N_MELS):
        lo, mid, hi = bins[m], bins[m + 1], bins[m + 2]
        if mid > lo:
            fb[m, lo:mid] = (np.arange(lo, mid) - lo) / (mid - lo)
        if hi > mid:
            fb[m, mid:hi] = (hi - np.arange(mid, hi)) / (hi - mid)
    return fb


def load_wav_as_mel(path):
    sr, audio = scipy.io.wavfile.read(path)

    # Convert to mono float32
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)
    if audio.dtype != np.float32 or audio.max() > 1.0:
        audio /= np.iinfo(np.int16).max  # normalise int16 range

    # Resample to TARGET_SR
    if sr != TARGET_SR:
        gcd = np.gcd(TARGET_SR, sr)
        audio = scipy.signal.resample_poly(audio, TARGET_SR // gcd, sr // gcd).astype(np.float32)

    # Trim or pad to TARGET_SAMPLES
    if len(audio) >= TARGET_SAMPLES:
        audio = audio[:TARGET_SAMPLES]
    else:
        audio = np.pad(audio, (0, TARGET_SAMPLES - len(audio)))

    # STFT — reflect-pad by N_FFT//2 on each side (matches librosa center=True)
    audio = np.pad(audio, N_FFT // 2, mode='reflect')
    _, _, S = scipy.signal.stft(audio, fs=TARGET_SR, nperseg=N_FFT,
                                noverlap=N_FFT - HOP_LENGTH,
                                boundary=None, padded=False)
    power = np.abs(S) ** 2  # (n_freqs, n_frames)

    mel = _mel_filterbank() @ power          # (40, n_frames)
    log_mel = np.log(mel + 1e-6)             # float32, ~[-14, 0]
    return log_mel.flatten().astype(np.float32)


def run(runner: DpuRunner, wav_path: str):
    print(f"Loading {wav_path} ...")
    mel = load_wav_as_mel(wav_path)
    print(f"Mel shape: (40, {len(mel) // 40})  —  running DPU inference ...")

    predicted, logits = runner.run(mel)

    # Softmax for display
    e = np.exp(logits - logits.max())
    probs = e / e.sum()

    print(f"\nPrediction: {predicted}\n")
    print(f"{'Class':<16} {'Logit':>6}  {'Prob':>7}")
    print("-" * 34)
    for cls, logit, prob in sorted(zip(CLASSES, logits, probs),
                                   key=lambda x: -x[2]):
        marker = " <--" if cls == predicted else ""
        print(f"{cls:<16} {logit:>6.1f}  {prob:>6.2%}{marker}")
