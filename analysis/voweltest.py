# analyze_batch.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

from vowel_v2 import (
    analyze_single_audio,
    STANDARD_MALE_FORMANTS,
    STANDARD_FEMALE_FORMANTS,
)

########################################
# 1. Map folder names (Korean) to internal keys
########################################
# Currently supports the six core monophthongs
VOWEL_MAP = {
    "아": "a (아)",
    "어": "eo (어)",
    "오": "o (오)",
    "우": "u (우)",
    "으": "eu (으)",
    "이": "i (이)",
}

VOWEL_COLORS = {
    "아": "#e74c3c",
    "어": "#9b59b6",
    "오": "#f39c12",
    "우": "#16a085",
    "으": "#2980b9",
    "이": "#34495e",
}


########################################
# 2. Analyze every file in a vowel folder
########################################
def analyze_vowel_folder(vowel_char: str, folder_path: str):
    """
    vowel_char example: "아"
    folder_path example: "./dataset/아"
    Returns a summary dict or None.
    """
    vowel_key = VOWEL_MAP.get(vowel_char)
    if vowel_key is None:
        print(f"[WARN] {vowel_char} is not mapped; skipping")
        return None

    # Collect every m4a/wav/mp3 file under the folder
    audio_files = []
    for ext in ("wav", "m4a", "mp3"):
        audio_files.extend(glob.glob(os.path.join(folder_path, f"*.{ext}")))

    if not audio_files:
        print(f"[WARN] {folder_path}: no audio detected; skipping")
        return None

    per_samples = []
    for path in audio_files:
        r = analyze_single_audio(path, vowel_key)
        if r is not None:
            per_samples.append(r)

    if not per_samples:
        print(f"[WARN] {folder_path}: analysis failed for every file; skipping")
        return None

    # Majority vote for gender
    genders = [r["gender"] for r in per_samples]
    gender_majority = max(set(genders), key=genders.count)

    # Aggregate metrics
    f1_vals = [r["f1"] for r in per_samples]
    f2_vals = [r["f2"] for r in per_samples]
    f0_vals = [r["f0"] for r in per_samples]
    score_vals = [r["score"] for r in per_samples]

    summary = {
        "vowel_char": vowel_char,      # e.g., Korean symbol name
        "vowel_key": vowel_key,        # e.g., romanized key
        "results": per_samples,        # raw results
        "gender_majority": gender_majority,
        "mean_f1": float(np.mean(f1_vals)),
        "mean_f2": float(np.mean(f2_vals)),
        "mean_f0": float(np.mean(f0_vals)),
        "mean_score": float(np.mean(score_vals)),
    }
    return summary


########################################
# 3. Plot all vowels in a single figure
########################################
def plot_overall_map(summaries, out_path):
    """
    summaries: list of per-vowel summaries (None filtered out)
    Plot gender-specific references and overlay each average point.
    """
    gender = summaries[0]["gender_majority"]
    ref_table = STANDARD_MALE_FORMANTS if gender == "Male" else STANDARD_FEMALE_FORMANTS

    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot all reference vowels (gender-specific) as grey X markers
    for key, ref in ref_table.items():
        ax.scatter(ref["f2"], ref["f1"], c="lightgray", marker="x", s=80)
        ax.text(ref["f2"]+10, ref["f1"]+10, key, color="gray", fontsize=8)

    # Plot each measured average
    for s in summaries:
        f1m = s["mean_f1"]
        f2m = s["mean_f2"]
        label = s["vowel_char"]  # Korean vowel label
        ax.scatter(f2m, f1m, c="red", s=160, alpha=0.8)
        ax.text(f2m+10, f1m+10, f"{label}", color="red", fontsize=10, fontweight="bold")

    ax.set_title(f"My Vowel Map (gender guess: {gender})")
    ax.set_xlabel("F2 (Hz) ← front ... back →")
    ax.set_ylabel("F1 (Hz) ← high tongue ... low tongue →")

    ax.invert_yaxis()  # Match traditional vowel chart orientation
    ax.invert_xaxis()

    ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close(fig)
    print(f"[plot_overall_map] Saved {out_path}")


########################################
# 3-bis. Per-vowel distribution (F1/F2 scatter)
########################################
def _sample_ellipse(points_f2, points_f1):
    """
    points_f2, points_f1: sequences of same length
    return (width, height, angle_deg) for 1-sigma ellipse
    """
    pts = np.array([points_f2, points_f1])
    if pts.shape[1] < 2:
        return None
    cov = np.cov(pts)
    if not np.all(np.isfinite(cov)):
        return None
    eigen_vals, eigen_vecs = np.linalg.eigh(cov)
    order = eigen_vals.argsort()[::-1]
    eigen_vals = eigen_vals[order]
    eigen_vecs = eigen_vecs[:, order]
    width = 2 * np.sqrt(eigen_vals[0])
    height = 2 * np.sqrt(eigen_vals[1])
    angle = np.degrees(np.arctan2(eigen_vecs[1, 0], eigen_vecs[0, 0]))
    return width, height, angle


def plot_vowel_distribution(summary, out_path, reference_gender=None):
    gender = reference_gender or summary["gender_majority"]
    ref_table = STANDARD_MALE_FORMANTS if gender == "Male" else STANDARD_FEMALE_FORMANTS
    vowel_key = summary["vowel_key"]
    ref = ref_table.get(vowel_key)

    f1_vals = np.array([r["f1"] for r in summary["results"]])
    f2_vals = np.array([r["f2"] for r in summary["results"]])

    fig, ax = plt.subplots(figsize=(6, 5))

    if ref:
        ax.scatter(ref["f2"], ref["f1"], c="green", marker="x", s=120, label="Reference target")
        ax.text(ref["f2"] + 10, ref["f1"] + 10, vowel_key, color="green", fontsize=9)
        ellipse = Ellipse(
            (ref["f2"], ref["f1"]),
            width=ref["f2_sd"] * 2,
            height=ref["f1_sd"] * 2,
            angle=0,
            color="green",
            alpha=0.15,
            label="Reference 1σ"
        )
        ax.add_patch(ellipse)

    ax.scatter(f2_vals, f1_vals, c="red", s=80, alpha=0.7, label="Samples")
    ax.scatter([summary["mean_f2"]], [summary["mean_f1"]], c="blue", s=150, marker="*", label="Sample mean")

    sample_ellipse = _sample_ellipse(f2_vals, f1_vals)
    if sample_ellipse:
        width, height, angle = sample_ellipse
        ell = Ellipse(
            (summary["mean_f2"], summary["mean_f1"]),
            width=width * 2,
            height=height * 2,
            angle=angle,
            linewidth=1.5,
            edgecolor="red",
            facecolor="none",
            linestyle="--",
            label="Sample spread (≈2σ)"
        )
        ax.add_patch(ell)

    title_gender = f"ref={gender}"
    ax.set_title(f"{summary['vowel_char']} ({vowel_key}) distribution ({title_gender})")
    ax.set_xlabel("F2 (Hz) ← front ... back →")
    ax.set_ylabel("F1 (Hz) ← high ... low →")
    ax.invert_yaxis()
    ax.invert_xaxis()
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close(fig)
    print(f"[plot_vowel_distribution] Saved {out_path}")


def plot_combined_distribution(summaries, out_path, blend=None):
    fig, ax = plt.subplots(figsize=(9, 7))

    # Plot male and female reference vowels
    male_plotted = False
    female_plotted = False
    for key, ref in STANDARD_MALE_FORMANTS.items():
        label = "Male reference" if not male_plotted else None
        ax.scatter(ref["f2"], ref["f1"], c="black", marker="x", s=80, label=label)
        male_plotted = True
    for key, ref in STANDARD_FEMALE_FORMANTS.items():
        label = "Female reference" if not female_plotted else None
        ax.scatter(ref["f2"], ref["f1"], c="gray", marker="+", s=80, label=label)
        female_plotted = True

    sample_label_used = set()
    mean_label_used = set()
    blend_label_used = False

    for summary in summaries:
        vch = summary["vowel_char"]
        color = VOWEL_COLORS.get(vch, "#e67e22")
        f1_vals = np.array([r["f1"] for r in summary["results"]])
        f2_vals = np.array([r["f2"] for r in summary["results"]])

        sample_label = f"{vch} samples" if vch not in sample_label_used else None
        ax.scatter(f2_vals, f1_vals, c=color, s=60, alpha=0.6, label=sample_label)
        sample_label_used.add(vch)

        mean_label = f"{vch} mean" if vch not in mean_label_used else None
        ax.scatter([summary["mean_f2"]], [summary["mean_f1"]], c=color, s=180, marker="*", edgecolors="k", linewidths=0.5, label=mean_label)
        mean_label_used.add(vch)

        if blend is not None:
            vowel_key = summary["vowel_key"]
            male_ref = STANDARD_MALE_FORMANTS.get(vowel_key)
            female_ref = STANDARD_FEMALE_FORMANTS.get(vowel_key)
            if male_ref and female_ref:
                f2_blend = male_ref["f2"] * (1 - blend) + female_ref["f2"] * blend
                f1_blend = male_ref["f1"] * (1 - blend) + female_ref["f1"] * blend
                blend_label = f"Blend ref (α={blend:.2f})" if not blend_label_used else None
                ax.scatter([f2_blend], [f1_blend], c=color, marker="D", s=100, label=blend_label)
                blend_label_used = True
                ax.plot(
                    [male_ref["f2"], female_ref["f2"]],
                    [male_ref["f1"], female_ref["f1"]],
                    color=color,
                    linestyle=":",
                    linewidth=1.0,
                    alpha=0.6
                )

        sample_ellipse = _sample_ellipse(f2_vals, f1_vals)
        if sample_ellipse:
            width, height, angle = sample_ellipse
            ell = Ellipse(
                (summary["mean_f2"], summary["mean_f1"]),
                width=width * 2,
                height=height * 2,
                angle=angle,
                edgecolor=color if color else "red",
                facecolor="none",
                linestyle="--",
                linewidth=1.2,
            )
            ax.add_patch(ell)

    title = "Sample F1/F2 distribution with male & female references"
    if blend is not None:
        title += f" (blend α={blend:.2f})"
    ax.set_title(title)
    ax.set_xlabel("F2 (Hz) ← front ... back →")
    ax.set_ylabel("F1 (Hz) ← high ... low →")
    ax.invert_yaxis()
    ax.invert_xaxis()
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8, loc="upper right", ncol=2)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close(fig)
    print(f"[plot_combined_distribution] Saved {out_path}")


########################################
# 4. main
########################################
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch vowel analysis and visualization."
    )
    parser.add_argument("data_root", help="Root directory containing vowel subfolders.")
    parser.add_argument("out_dir", help="Output directory for reports and plots.")
    parser.add_argument(
        "--blend",
        type=float,
        default=None,
        help="Optional blend factor between male (0) and female (1) references to visualize."
    )
    args = parser.parse_args()

    if args.blend is not None and not (0.0 <= args.blend <= 1.0):
        raise SystemExit("--blend must be between 0.0 and 1.0")

    data_root = args.data_root
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    vowel_dirs = ["아", "어", "오", "우", "으", "이"]

    all_summaries = []
    for vch in vowel_dirs:
        folder_path = os.path.join(data_root, vch)
        if not os.path.isdir(folder_path):
            continue

        print(f"=== {vch} ({folder_path}) ===")
        s = analyze_vowel_folder(vch, folder_path)
        if s is None:
            print(" -> failed/skipped\n")
            continue

        all_summaries.append(s)

        # Write per-vowel report file
        report_path = os.path.join(out_dir, f"{vch}_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"[{vch}] vowel_key={s['vowel_key']}\n")
            f.write(f"gender_majority={s['gender_majority']}\n")
            f.write(f"mean_f0={s['mean_f0']:.2f} Hz\n")
            f.write(f"mean_f1={s['mean_f1']:.2f} Hz\n")
            f.write(f"mean_f2={s['mean_f2']:.2f} Hz\n")
            f.write(f"mean_score={s['mean_score']:.1f} /100\n\n")

            f.write("Samples:\n")
            for r in s["results"]:
                f.write(
                    f" - {os.path.basename(r['audio_path'])}: "
                    f"f0={r['f0']:.1f}, f1={r['f1']:.1f}, f2={r['f2']:.1f}, "
                    f"score={r['score']}, gender={r['gender']}\n"
                )
                f.write(f"   feedback: {r['feedback']}\n")
                if r['quality_hint']:
                    f.write(f"   quality:  {r['quality_hint']}\n")
        print(f" -> wrote {report_path}\n")

        dist_plot_path = os.path.join(out_dir, f"{vch}_distribution.png")
        plot_vowel_distribution(s, dist_plot_path)

        male_plot_path = os.path.join(out_dir, f"{vch}_distribution_male_ref.png")
        plot_vowel_distribution(s, male_plot_path, reference_gender="Male")

        female_plot_path = os.path.join(out_dir, f"{vch}_distribution_female_ref.png")
        plot_vowel_distribution(s, female_plot_path, reference_gender="Female")

    # Overall plot plus overall summary
    if all_summaries:
        overall_plot_path = os.path.join(out_dir, "overall_vowel_map.png")
        plot_overall_map(all_summaries, overall_plot_path)

        combined_plot_path = os.path.join(
            out_dir,
            "combined_distribution_blend.png" if args.blend is not None else "combined_distribution.png"
        )
        plot_combined_distribution(all_summaries, combined_plot_path, blend=args.blend)

        summary_all_txt = os.path.join(out_dir, "summary_all.txt")
        with open(summary_all_txt, "w", encoding="utf-8") as f:
            gender_ref = all_summaries[0]["gender_majority"]
            f.write(f"Global gender guess: {gender_ref}\n\n")
            for s in all_summaries:
                f.write(
                    f"{s['vowel_char']} ({s['vowel_key']}): "
                    f"f1={s['mean_f1']:.1f}, "
                    f"f2={s['mean_f2']:.1f}, "
                    f"score={s['mean_score']:.1f}, "
                    f"gender={s['gender_majority']}\n"
                )
        print(f" -> wrote {summary_all_txt}")
    else:
        print("No valid vowel folders processed.")
