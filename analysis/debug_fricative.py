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
    plt.barh([label], [value], alpha=0.7)
    if target is not None:
        plt.axvline(target, linestyle="--", label="target")
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
    plt.axvspan(fric_t0, fric_t1, alpha=0.3, label="frication")
    plt.xlabel("Time (s)")
    plt.ylabel("HF / LF")
    plt.title("HF/LF Ratio Envelope (Affricate)")
    plt.legend()
    plt.tight_layout()
    plt.show()


# ------------------------------------------------------------
# Ternary (triangle) visualization: ㅉ / ㅈ / ㅊ proximity map
# ------------------------------------------------------------
def _normalize_softscores(softscores: dict, temperature: float = 10.0) -> tuple[float, float, float]:
    """
    Convert scores -> softmax probabilities for ternary plotting.
    temperature 낮을수록(예: 6~10) 차이가 더 강조됨.
    Returns (wF, wL, wA) for fortis(ㅉ), lenis(ㅈ), aspirated(ㅊ)
    """
    f = float(softscores.get("fortis", 0.0) or 0.0)
    l = float(softscores.get("lenis", 0.0) or 0.0)
    a = float(softscores.get("aspirated", 0.0) or 0.0)

    x = np.array([f, l, a], dtype=np.float64) / max(1e-9, float(temperature))
    x = x - np.max(x)  # stability
    p = np.exp(x)
    p = p / np.sum(p)

    # return wF, wL, wA
    return float(p[0]), float(p[1]), float(p[2])


def _barycentric_to_xy(wF: float, wL: float, wA: float, F, L, A):
    """
    XY = wF*F + wL*L + wA*A
    """
    x = wF * F[0] + wL * L[0] + wA * A[0]
    y = wF * F[1] + wL * L[1] + wA * A[1]
    return x, y


def plot_affricate_ternary(softscores: dict, target: str, detected: str, final_score: float | None):
    """
    Triangle plot (ternary-like) showing closeness to:
      ㅉ (fortis), ㅈ (lenis), ㅊ (aspirated)
    Uses normalized softscores as barycentric weights.
    """
    # Triangle vertices (nice equilateral-ish triangle)
    F = (0.0, 0.0)                 # left-bottom: ㅉ
    L = (1.0, 0.0)                 # right-bottom: ㅈ
    A = (0.5, np.sqrt(3) / 2.0)    # top: ㅊ

    wF, wL, wA = _normalize_softscores(softscores)
    ux, uy = _barycentric_to_xy(wF, wL, wA, F, L, A)

    # "Target" marker: slightly inside the vertex (looks better than exact corner)
    eps = 0.06
    if target == "fortis":
        t_wF, t_wL, t_wA = (1 - 2 * eps, eps, eps)
    elif target == "lenis":
        t_wF, t_wL, t_wA = (eps, 1 - 2 * eps, eps)
    else:  # aspirated
        t_wF, t_wL, t_wA = (eps, eps, 1 - 2 * eps)

    tx, ty = _barycentric_to_xy(t_wF, t_wL, t_wA, F, L, A)

    plt.figure(figsize=(6.2, 6.2))

    # Triangle outline
    tri_x = [A[0], F[0], L[0], A[0]]
    tri_y = [A[1], F[1], L[1], A[1]]
    plt.plot(tri_x, tri_y, linewidth=1.5, alpha=0.7)

    # Vertex labels
    plt.text(A[0], A[1], "ㅊ", ha="center", va="bottom", fontsize=14, fontweight="bold")
    plt.text(F[0], F[1], "ㅉ", ha="right", va="top", fontsize=14, fontweight="bold")
    plt.text(L[0], L[1], "ㅈ", ha="left", va="top", fontsize=14, fontweight="bold")

    # Target marker
    plt.scatter([tx], [ty], s=140, facecolors="red", label="Target")

    # User marker
    plt.scatter([ux], [uy], s=120, facecolors="yellow", label="User")

    # Small annotation
    title = "ㅉ / ㅈ / ㅊ Map"

    plt.title(title)
    plt.axis("equal")
    plt.axis("off")

    plt.legend(loc="upper right")
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
    softscores = evals.get("softscores", {}) or {}

    # --------------------------------------------------------
    # Ternary proximity map (ㅉ / ㅈ / ㅊ)
    # --------------------------------------------------------
    target = result.get("targets", {}).get("affricate")
    detected = evals.get("detected_affricate")
    final_score = evals.get("final_score", None)
    if isinstance(final_score, (int, float)):
        final_score = float(final_score)
    else:
        final_score = None

    if softscores and target and detected:
        plot_affricate_ternary(
            softscores=softscores,
            target=target,
            detected=detected,
            final_score=final_score,
        )
    else:
        print("\n[Warning] Missing softscores/target/detected for ternary plot.")

if __name__ == "__main__":
    main()
