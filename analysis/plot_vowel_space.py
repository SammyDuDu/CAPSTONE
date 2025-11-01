#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggregate vowel samples into a single vowel-space plot with text labels.
"""

import argparse
import os
from pathlib import Path
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from vowel_v1 import convert_to_wav, analyze_vowel_and_pitch

SUPPORTED_EXTENSIONS = {".wav", ".m4a", ".mp3"}


def find_audio_files(audio_dir: Path):
    for path in sorted(audio_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def analyze_file(audio_path: Path):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        if not convert_to_wav(str(audio_path), str(tmp_path)):
            print(f"[WARN] Conversion failed for {audio_path.name}")
            return None
        f1, f2, _, _ = analyze_vowel_and_pitch(str(tmp_path))
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass

    if not (f1 and f2):
        print(f"[WARN] Analysis failed for {audio_path.name}")
        return None

    return {"label": audio_path.stem, "f1": f1, "f2": f2}


def plot_results(results, output_image: Path):
    fig, ax = plt.subplots(figsize=(10, 8))
    f1_values = [entry["f1"] for entry in results]
    f2_values = [entry["f2"] for entry in results]

    # Invisible scatter ensures axes scale to the data range
    ax.scatter(f2_values, f1_values, s=10, alpha=0.0)

    for entry in results:
        ax.text(entry["f2"], entry["f1"], entry["label"], fontsize=14,
                ha="center", va="center")
    ax.set_xlabel("F2 (Hz) ← Front / Back →")
    ax.set_ylabel("F1 (Hz) ← High / Low →")
    ax.set_title("Combined Vowel Space")
    if len(f1_values) > 1:
        f1_span = max(f1_values) - min(f1_values)
        f2_span = max(f2_values) - min(f2_values)
        f1_pad = max(50.0, 0.05 * f1_span)
        f2_pad = max(50.0, 0.05 * f2_span)
    else:
        f1_pad = f2_pad = 100.0
    ax.set_xlim(min(f2_values) - f2_pad, max(f2_values) + f2_pad)
    ax.set_ylim(min(f1_values) - f1_pad, max(f1_values) + f1_pad)
    ax.invert_yaxis()
    ax.invert_xaxis()
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    output_image.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_image)
    plt.close(fig)
    print(f"[INFO] Plot saved to {output_image}")


def main():
    parser = argparse.ArgumentParser(
        description="Plot all vowel samples in a single vowel space with labels."
    )
    parser.add_argument(
        "audio_dir",
        nargs="?",
        default="../sample/check_vowel",
        help="Directory containing vowel audio samples (default: ../sample/check_vowel)",
    )
    parser.add_argument(
        "--output",
        default="./output/combined_vowel_space_v.png",
        help="Path to save the resulting plot (default: ./output/combined_vowel_space.png)",
    )
    args = parser.parse_args()

    audio_dir = Path(args.audio_dir).resolve()
    if not audio_dir.exists():
        raise SystemExit(f"[ERROR] Audio directory not found: {audio_dir}")

    print(f"[INFO] Loading samples from {audio_dir}")
    results = []
    for audio_file in find_audio_files(audio_dir):
        print(f"  - Processing {audio_file.name}")
        analysis = analyze_file(audio_file)
        if analysis:
            results.append(analysis)

    if not results:
        raise SystemExit("[ERROR] No valid analyses completed.")

    output_path = Path(args.output).resolve()
    plot_results(results, output_path)


if __name__ == "__main__":
    main()
