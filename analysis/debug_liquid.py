''''
# analysis/debug_liquid.py
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

from analysis.liquid import analyze_liquid

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    if len(sys.argv) < 3:
        print("Usage: python analysis/debug_liquid.py <wav_path> <syllable>")
        print("Example: python analysis/debug_liquid.py sample/라.wav 라")
        sys.exit(1)

    wav_path = sys.argv[1]
    syllable = sys.argv[2]

    result = analyze_liquid(wav_path, syllable)

    print("\n=== Feedback ===")
    print(result.get("feedback", {}).get("text", "(no feedback)"))

    print("\n=== Result JSON ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

'''

# analysis/debug_liquid.py
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

from analysis.liquid import analyze_liquid  # noqa: E402


# ------------------------------------------------------------
# Simple gauge bar utility
# ------------------------------------------------------------
def plot_gauge(
    value,
    label,
    title,
    xmin,
    xmax,
    ok_range=None,        # (lo, hi)
    warn_range=None,      # (lo, hi)
    reverse_ok=False,     # if True, "lower is better"
):
    """
    Draw a 1D gauge with zones.
    - ok_range: green zone
    - warn_range: yellow zone
    - otherwise red-ish background
    """
    plt.figure(figsize=(7.2, 1.9))

    # background zones
    # full range = light gray
    plt.axvspan(xmin, xmax, alpha=0.08)

    if warn_range is not None:
        plt.axvspan(warn_range[0], warn_range[1], alpha=0.12)

    if ok_range is not None:
        plt.axvspan(ok_range[0], ok_range[1], alpha=0.18)

    # value bar
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        plt.barh([label], [0], alpha=0.0)
        plt.xlim(xmin, xmax)
        plt.title(f"{title}  (missing)")
        plt.tight_layout()
        plt.show()
        return

    v = float(np.clip(value, xmin, xmax))
    plt.barh([label], [v], alpha=0.75)

    # marker line at value
    plt.axvline(v, linestyle="--", linewidth=1.2)

    # annotate
    plt.text(v, 0, f"  {value:.2f}", va="center", fontsize=10)

    plt.xlim(xmin, xmax)
    plt.title(title)
    plt.tight_layout()
    plt.show()


def plot_softscores_breakdown(softscores: dict, title: str):
    if not softscores:
        return
    keys = list(softscores.keys())
    vals = [float(softscores[k]) for k in keys]

    plt.figure(figsize=(7.2, 3.0))
    plt.bar(keys, vals, alpha=0.8)
    plt.ylim(0, 100)
    plt.ylabel("Score (0–100)")
    plt.title(title)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.show()


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    if len(sys.argv) < 3:
        print("Usage: python analysis/debug_liquid.py <wav_path> <syllable>")
        print("Example: python analysis/debug_liquid.py sample/consonant_yuna/라.wav 라")
        sys.exit(1)

    wav_path = sys.argv[1]
    syllable = sys.argv[2]

    result = analyze_liquid(wav_path, syllable)

    print("\n=== Feedback ===")
    print(result.get("feedback", {}).get("text", "(no feedback)"))

    print("\n=== Result JSON ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    feats = result.get("features", {}) or {}
    evals = result.get("evaluation", {}) or {}

    final_score = evals.get("final_score", 0.0)
    is_rejected = bool(evals.get("is_rejected", False))
    reject_reason = evals.get("reject_reason", "")

    # --------------------------------------------------------
    # 1) User-friendly "3-condition" gauges
    # --------------------------------------------------------
    # These ranges are heuristic UI ranges, NOT scientific truth.
    # They are chosen to make feedback intuitive.

    # (A) Tongue tap clarity (closure depth)
    # Typical OK: ~6 to 18 dB (too low => skipped tap; too high => too hard/stop-like)
    plot_gauge(
        value=feats.get("closure_depth_db"),
        label="Tongue tap",
        title="Did your tongue touch happen clearly? (for '라')",
        xmin=0.0,
        xmax=30.0,
        warn_range=(3.5, 6.0),   # borderline
        ok_range=(6.0, 18.0),
    )

    # (B) Hiss amount (frication ratio peak)
    # Lower is better. /s/ tends to be high.
    # OK: <= ~2.0, warning: 2.0–2.6, bad: >2.6
    plot_gauge(
        value=feats.get("frication_ratio_peak"),
        label="Hiss",
        title="Is there too much 'hiss' (like '사')?",
        xmin=0.0,
        xmax=5.0,
        warn_range=(2.0, 2.6),
        ok_range=(0.0, 2.0),
        reverse_ok=True,
    )

    # (C) Voicing (0..1)
    # OK: >= 0.65, warning: 0.35–0.65, bad: <0.35
    plot_gauge(
        value=feats.get("voiced_fraction"),
        label="Voicing",
        title="Is your voice ON (a gentle hum) during '라'?",
        xmin=0.0,
        xmax=1.0,
        warn_range=(0.35, 0.65),
        ok_range=(0.65, 1.0),
    )

    # Optional extra: centroid (helps show "noisy vs smooth", but can be vowel-influenced)
    if feats.get("spectral_centroid_hz") is not None:
        plot_gauge(
            value=feats.get("spectral_centroid_hz"),
            label="Smoothness",
            title="Overall smoothness (lower = smoother, less hiss)",
            xmin=0.0,
            xmax=3000.0,
            warn_range=(900.0, 1400.0),
            ok_range=(0.0, 900.0),
            reverse_ok=True,
        )

    # --------------------------------------------------------
    # 2) Score breakdown (why the final score is high/low)
    # --------------------------------------------------------
    softscores = evals.get("softscores", {}) or {}
    status = "REJECTED" if is_rejected else "ACCEPTED"
    extra = f" (reason: {reject_reason})" if is_rejected and reject_reason else ""
    plot_softscores_breakdown(
        softscores,
        title=f"Score breakdown for '라'  |  {status}{extra}  |  final={final_score:.1f}",
    )

    # --------------------------------------------------------
    # 3) Small console hint (useful when debugging false positives)
    # --------------------------------------------------------
    if is_rejected:
        print("\n[Note] This result was REJECTED by the safety gates.")
        print(f"       reject_reason = {reject_reason}")
        print("       (So even if some acoustic features look 'okay', the system thinks it's not really '라'.)")
    else:
        # If confidence exists, print it
        if "confidence" in evals:
            print(f"\n[Info] confidence = {evals.get('confidence'):.2f}")

if __name__ == "__main__":
    main()
