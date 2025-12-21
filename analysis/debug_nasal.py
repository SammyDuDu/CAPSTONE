# analysis/debug_nasal.py
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

from analysis.nasal import analyze_nasal

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    if len(sys.argv) < 3:
        print("Usage: python analysis/debug_nasal.py <wav_path> <syllable>")
        print("Example: python analysis/debug_nasal.py sample/마.wav 마")
        sys.exit(1)

    wav_path = sys.argv[1]
    syllable = sys.argv[2]

    result = analyze_nasal(wav_path, syllable)

    print("\n=== Feedback ===")
    print(result.get("feedback", {}).get("text", "(no feedback)"))

    print("\n=== Result JSON ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
