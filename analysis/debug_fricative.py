# analysis/debug_fricative.py
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

from analysis.fricative import analyze_fricative  # noqa: E402


# ------------------------------------------------------------
# Helper: pick 3-class keys from softscores
# ------------------------------------------------------------
def _pick_fricative_keys(softscores: dict):
    if not softscores:
        return None

    keys = set(softscores.keys())
    patterns = [
        ("fortis", "lenis", "glottal"),
        ("fortis", "lenis", "h"),
        ("ss", "s", "h"),
        ("tense", "plain", "h"),
        ("ㅆ", "ㅅ", "ㅎ"),
    ]

    for k_ss, k_s, k_h in patterns:
        if k_ss in keys and k_s in keys and k_h in keys:
            return (k_ss, k_s, k_h)

    return None


def _softmax3(a, b, c, temperature=10.0):
    x = np.array([a, b, c], dtype=np.float64) / max(1e-9, float(temperature))
    x = x - np.max(x)
    p = np.exp(x)
    p = p / np.sum(p)
    return float(p[0]), float(p[1]), float(p[2])


# ------------------------------------------------------------
# Visualization: ㅆ — ㅅ — ㅎ slider (SAVE IMAGE)
# ------------------------------------------------------------
def plot_fricative_slider(
    user_pos: float,
    target_label: str | None,
    detected_label: str | None,
    save_path: Path,
):
    """
    user_pos: 0.0 ~ 1.0
      0.0 = ㅆ
      0.5 = ㅅ
      1.0 = ㅎ
    """
    user_pos = float(np.clip(user_pos, 0.0, 1.0))

    plt.figure(figsize=(7.5, 2.0))

    # baseline
    plt.plot([0, 1], [0, 0], linewidth=6, alpha=0.25)

    # ticks
    plt.scatter([0, 0.5, 1.0], [0, 0, 0], s=90, alpha=0.6)
    plt.text(0.0, -0.15, "ㅆ", ha="center", va="top", fontsize=15, fontweight="bold")
    plt.text(0.5, -0.15, "ㅅ", ha="center", va="top", fontsize=15, fontweight="bold")
    plt.text(1.0, -0.15, "ㅎ", ha="center", va="top", fontsize=15, fontweight="bold")

    # user marker
    plt.scatter([user_pos], [0], s=260, zorder=5)
    plt.text(user_pos, 0.12, "You", ha="center", va="bottom", fontsize=11)

    title = "Which does it sound closer to?"
    if target_label or detected_label:
        title += f"\n(target: {target_label or '?'}, detected: {detected_label or '?'})"
    plt.title(title)

    plt.ylim(-0.4, 0.4)
    plt.xlim(-0.05, 1.05)
    plt.axis("off")
    plt.tight_layout()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    if len(sys.argv) < 3:
        print("Usage: python analysis/debug_fricative.py <wav_path> <syllable>")
        sys.exit(1)

    wav_path = sys.argv[1]
    syllable = sys.argv[2]

    result = analyze_fricative(wav_path, syllable)

    print("\n=== Feedback ===")
    print(result.get("feedback", {}).get("text", "(no feedback)"))

    print("\n=== Result JSON ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    evals = result.get("evaluation", {}) or {}
    softscores = evals.get("softscores", {}) or {}

    # --------------------------------------------------------
    # Slider position from softscores
    # --------------------------------------------------------
    keys = _pick_fricative_keys(softscores)
    if keys is None:
        print("[Warning] Cannot find 3-class softscores for fricative.")
        return

    k_ss, k_s, k_h = keys
    s_ss = float(softscores.get(k_ss, 0.0) or 0.0)
    s_s = float(softscores.get(k_s, 0.0) or 0.0)
    s_h = float(softscores.get(k_h, 0.0) or 0.0)

    w_ss, w_s, w_h = _softmax3(s_ss, s_s, s_h, temperature=10.0)

    # 0=ㅆ, 0.5=ㅅ, 1=ㅎ
    user_pos = 0.0 * w_ss + 0.5 * w_s + 1.0 * w_h

    target = result.get("targets", {}).get("fricative")
    detected = evals.get("detected_fricative")

    def pretty(x):
        if x in ("fortis", "tense", "ss", "ㅆ"):
            return "ㅆ"
        if x in ("lenis", "plain", "s", "ㅅ"):
            return "ㅅ"
        if x in ("glottal", "h", "ㅎ"):
            return "ㅎ"
        return None

    # --------------------------------------------------------
    # Save image
    # --------------------------------------------------------
    out_path = Path("debug_plots") / f"{target}.png"

    plot_fricative_slider(
        user_pos=user_pos,
        target_label=pretty(target),
        detected_label=pretty(detected),
        save_path=out_path,
    )

    print(f"\n[Saved] Fricative feedback image → {out_path}")


if __name__ == "__main__":
    main()
