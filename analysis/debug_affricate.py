# analysis/debug_affricate.py
import sys
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

# ------------------------------------------------------------
# Path setup (project root)
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.affricate import analyze_affricate
from analysis.affricate import bandpass, _rms_envelope, load_sound

# ------------------------------------------------------------
# Simple bar plot utility
# ------------------------------------------------------------
def plot_bar(value, target, label, title, xmax=None):
    plt.figure(figsize=(6, 1.8))
    plt.barh([label], [value], color="tab:blue", alpha=0.7)
    if target is not None:
        plt.axvline(target, color="red", linestyle="--", label="target")
        plt.legend()
    if xmax:
        plt.xlim(0, xmax)
    plt.title(title)
    plt.tight_layout()
    plt.show()

# ------------------------------------------------------------
# HF/LF ratio envelope plot
# ------------------------------------------------------------
def plot_hf_lf_ratio(y, sr, fric_t0, fric_t1):
    y_hf = bandpass(y, sr, 1500, 8000)
    y_lf = bandpass(y, sr, 300, 1500)

    rms_hf, win, hop = _rms_envelope(y_hf, sr)
    rms_lf, _, _ = _rms_envelope(y_lf, sr)

    ratio = rms_hf / (rms_lf + 1e-12)
    times = np.arange(len(ratio)) * hop / sr

    plt.figure(figsize=(8, 3))
    plt.plot(times, ratio, label="HF/LF ratio")
    plt.axvspan(fric_t0, fric_t1, color="orange", alpha=0.3, label="frication")
    plt.xlabel("Time (s)")
    plt.ylabel("HF / LF")
    plt.title("HF/LF Ratio Envelope (Affricate)")
    plt.legend()
    plt.tight_layout()
    plt.show()


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    if len(sys.argv) < 3:
        print("Usage: python analysis/debug_affricate.py <wav_path> <syllable>")
        sys.exit(1)

    wav_path = sys.argv[1]
    syllable = sys.argv[2]

    result = analyze_affricate(wav_path, syllable)

    print("\n=== Feedback ===")
    print(result.get("feedback", {}).get("text", "(no feedback)"))

    print("\n=== Result JSON ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    feats = result.get("features", {})
    evals = result.get("evaluation", {})

    # --------------------------------------------------------
    # Bars (user-facing intuition)
    # --------------------------------------------------------
    if feats.get("vot_ms") is not None:
        plot_bar(
            feats["vot_ms"],
            target=None,
            label="VOT (ms)",
            title="Voice Onset Time"
        )

    if feats.get("frication_duration_ms") is not None:
        plot_bar(
            feats["frication_duration_ms"],
            target=None,
            label="Frication (ms)",
            title="Frication Duration"
        )

    if feats.get("spectral_centroid_hz") is not None:
        plot_bar(
            feats["spectral_centroid_hz"],
            target=None,
            label="Centroid (Hz)",
            title="Frication Sharpness"
        )

    # --------------------------------------------------------
    # HF/LF ratio envelope (developer debug)
    # --------------------------------------------------------
    snd, y, sr = load_sound(wav_path)

    fric_t0 = feats.get("fric_start_t", None)
    fric_t1 = feats.get("fric_end_t", None)

    # If timing info missing, approximate using analysis window
    if fric_t0 is None or fric_t1 is None:
        # fallback: assume first 200 ms after onset
        fric_t0 = 0.0
        fric_t1 = 0.2

    plot_hf_lf_ratio(y, sr, fric_t0, fric_t1)


if __name__ == "__main__":
    main()
