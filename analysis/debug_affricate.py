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

from analysis.affricate import analyze_affricate  # noqa: E402


# ------------------------------------------------------------
# Helper: pick 3-class keys from softscores (fortis/lenis/aspirated)
# ------------------------------------------------------------
def _pick_affricate_keys(softscores: dict):
    if not softscores:
        return None

    keys = set(softscores.keys())
    patterns = [
        ("fortis", "lenis", "aspirated"),
        ("tense", "plain", "aspirated"),
        ("ㅉ", "ㅈ", "ㅊ"),
    ]

    for k_f, k_l, k_a in patterns:
        if k_f in keys and k_l in keys and k_a in keys:
            return (k_f, k_l, k_a)

    # fallback: try to infer by substring
    def find_key(cands):
        for c in cands:
            for k in keys:
                if c == k:
                    return k
        for c in cands:
            for k in keys:
                if c in k:
                    return k
        return None

    k_f = find_key(["fortis", "tense", "ㅉ"])
    k_l = find_key(["lenis", "plain", "ㅈ"])
    k_a = find_key(["aspirated", "ㅊ"])

    if k_f and k_l and k_a:
        return (k_f, k_l, k_a)

    return None


def _softmax3(a, b, c, temperature=10.0):
    x = np.array([a, b, c], dtype=np.float64) / max(1e-9, float(temperature))
    x = x - np.max(x)
    p = np.exp(x)
    p = p / np.sum(p)
    return float(p[0]), float(p[1]), float(p[2])


# ------------------------------------------------------------
# Visualization: ㅉ — ㅈ — ㅊ slider (SAVE IMAGE)
# ------------------------------------------------------------
def plot_affricate_slider(
    user_pos: float,
    target_label: str | None,
    detected_label: str | None,
    save_path: Path,
):
    """
    user_pos: 0.0 ~ 1.0
      0.0 = ㅉ (fortis)
      0.5 = ㅈ (lenis)
      1.0 = ㅊ (aspirated)
    """
    user_pos = float(np.clip(user_pos, 0.0, 1.0))

    plt.figure(figsize=(7.5, 2.0))

    # baseline
    plt.plot([0, 1], [0, 0], linewidth=6, alpha=0.25)

    # ticks
    plt.scatter([0, 0.5, 1.0], [0, 0, 0], s=90, alpha=0.6)
    plt.text(0.0, -0.15, "ㅉ", ha="center", va="top", fontsize=15, fontweight="bold")
    plt.text(0.5, -0.15, "ㅈ", ha="center", va="top", fontsize=15, fontweight="bold")
    plt.text(1.0, -0.15, "ㅊ", ha="center", va="top", fontsize=15, fontweight="bold")

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
        print("Usage: python analysis/debug_affricate.py <wav_path> <syllable>")
        sys.exit(1)

    wav_path = sys.argv[1]
    syllable = sys.argv[2]

    result = analyze_affricate(wav_path, syllable)

    print("\n=== Feedback ===")
    print(result.get("feedback", {}).get("text", "(no feedback)"))

    print("\n=== Result JSON ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    evals = result.get("evaluation", {}) or {}
    softscores = evals.get("softscores", {}) or {}

    # --------------------------------------------------------
    # Slider position from softscores
    # --------------------------------------------------------
    keys = _pick_affricate_keys(softscores)
    if keys is None:
        print("[Warning] Cannot find 3-class softscores for affricate.")
        return

    k_f, k_l, k_a = keys
    s_f = float(softscores.get(k_f, 0.0) or 0.0)
    s_l = float(softscores.get(k_l, 0.0) or 0.0)
    s_a = float(softscores.get(k_a, 0.0) or 0.0)

    w_f, w_l, w_a = _softmax3(s_f, s_l, s_a, temperature=10.0)

    # 0=ㅉ, 0.5=ㅈ, 1=ㅊ
    user_pos = 0.0 * w_f + 0.5 * w_l + 1.0 * w_a

    target = result.get("targets", {}).get("affricate")
    detected = evals.get("detected_affricate")

    def pretty(x):
        if x in ("fortis", "tense", "ㅉ"):
            return "ㅉ"
        if x in ("lenis", "plain", "ㅈ"):
            return "ㅈ"
        if x in ("aspirated", "ㅊ"):
            return "ㅊ"
        return None

    # --------------------------------------------------------
    # Save image
    # --------------------------------------------------------
    out_path = Path("debug_plots") / f"{syllable}_affricate_slider.png"

    plot_affricate_slider(
        user_pos=user_pos,
        target_label=pretty(target),
        detected_label=pretty(detected),
        save_path=out_path,
    )

    print(f"\n[Saved] Affricate feedback image → {out_path}")


if __name__ == "__main__":
    main()
