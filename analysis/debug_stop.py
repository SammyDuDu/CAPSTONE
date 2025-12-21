# analysis/debug_stop_plot.py
import sys
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "AppleGothic"   # macOS 한글 폰트
plt.rcParams["axes.unicode_minus"] = False    # 마이너스 기호 깨짐 방지

# 실행 위치가 어디든 analysis 패키지를 찾게 만들기 (프로젝트 루트 기준)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.stops import analyze_stop, F0Calibration

import math
import numpy as np

def phonation_to_syllable_labels(place: str) -> dict:
    """
    place(labial/alveolar/velar)에 따라 fortis/lenis/aspirated의 표시 라벨을 음절로 매핑
    """
    mapping = {
        "labial":  {"lenis": "ㅂ",  "fortis": "ㅃ", "aspirated": "ㅍ"},
        "alveolar":{"lenis": "ㄷ",  "fortis": "ㄸ", "aspirated": "ㅌ"},
        "velar":   {"lenis": "ㄱ",  "fortis": "ㄲ", "aspirated": "ㅋ"},
    }
    return mapping.get(place, {"lenis": "lenis", "fortis": "fortis", "aspirated": "aspirated"})

def classify_by_reference_ellipse(x, y, vot_ranges, f0z_targets):
    """
    reference를 타원(ellipse)로 보고, normalized distance가 최소인 그룹을 선택.
    dist = ((x-xc)/xr)^2 + ((y-yc)/yr)^2
    xr = (high-low)/2, yr = tol
    """
    best_phon = None
    best_d = float("inf")
    for phon in ["fortis", "lenis", "aspirated"]:
        if phon not in vot_ranges or phon not in f0z_targets:
            continue
        lo, hi = vot_ranges[phon]["low"], vot_ranges[phon]["high"]
        xc = vot_ranges[phon]["center"]
        yc = f0z_targets[phon]["center"]
        xr = max((hi - lo) / 2.0, 1e-6)
        yr = max(f0z_targets[phon]["tol"], 1e-6)
        d = ((x - xc) / xr) ** 2 + ((y - yc) / yr) ** 2
        if d < best_d:
            best_d = d
            best_phon = phon
    return best_phon, best_d

def x_from_place_softscores(place_softscores: dict, temp: float = 12.0) -> float:
    """
    place_softscores (0~100 같은 점수) -> 1D axis x position (0~3)
    - labial center: 0.5
    - alveolar center: 1.5
    - velar center: 2.5

    temp: 클수록(예: 20) 더 '부드럽게' 평균, 작을수록(예: 5) 더 '승자독식'에 가까움
    """
    centers = {"labial": 0.5, "alveolar": 1.5, "velar": 2.5}

    # 누락 방지
    scores = {k: float(place_softscores.get(k, 0.0)) for k in centers.keys()}

    # 안정적인 softmax (점수가 0~100이므로 temp로 스케일 조절)
    max_s = max(scores.values())
    exps = {k: math.exp((scores[k] - max_s) / max(temp, 1e-6)) for k in scores}
    Z = sum(exps.values()) or 1.0
    w = {k: exps[k] / Z for k in exps}

    # 가중평균 위치
    x = sum(w[k] * centers[k] for k in centers)
    return x

def place_to_x_center(place: str) -> float:
    # labial/alveolar/velar -> x center (0.5, 1.5, 2.5)
    centers = {"labial": 0.5, "alveolar": 1.5, "velar": 2.5}
    return centers.get(place, 1.5)

def place_to_group_label(place: str) -> str:
    labels = {"labial": "ㅂ/ㅃ/ㅍ", "alveolar": "ㄷ/ㄸ/ㅌ", "velar": "ㄱ/ㄲ/ㅋ"}
    return labels.get(place, str(place))

def plot_stop_debug(result: dict, out_dir: Path | None = None, show: bool = True):
    softscores = result["evaluation"].get("place_softscores", {})
    x_user = x_from_place_softscores(softscores, temp=12.0)
    syllable = result.get("syllable", "?")
    plots = result["evaluation"]["plots"]
    targets = result.get("targets", {})

    f2_centers = plots["f2_centers_hz"]          # dict: place -> center_hz
    f2_user = plots["f2_user_hz"]                # float | None
    f2_tol = plots["f2_tolerance_hz"]            # float

    vot_point = plots["vot_f0_point"]            # {"x_vot_ms":..., "y_f0_z":...}
    vot_ranges = plots["vot_reference_ranges_ms"]# dict phonation -> {low/high/center}
    f0z_targets = plots["f0z_reference_targets"] # dict phonation -> {center/tol}

    # ---------------------------
    # (A) Place axis plot (Service UX with color separation)
    # ---------------------------

    group_labels = ["ㅂ/ㅃ/ㅍ", "ㄷ/ㄸ/ㅌ", "ㄱ/ㄲ/ㅋ"]  # left -> right

    axis_color = "#1f77b4"   # 축/경계/화살표 (중립 파랑)
    target_color = "#d62728" # 목표: 빨강
    user_color = "#ffbf00"   # 사용자: 노란색
    text_color = "black"     # detected 문구

    detected_place = result["evaluation"].get("detected_place", None)
    target_place = targets.get("place", None)

    softscores = result["evaluation"].get("place_softscores", {}) or {}
    place_conf = float(result["evaluation"].get("place_confidence", 0.0) or 0.0)

    # ▲ 사용자 위치 (detected 기준 스냅)
    x_user = place_to_x_center(detected_place) if detected_place else 1.5

    # ★ 타겟 위치
    x_target = place_to_x_center(target_place) if target_place else None

    detected_group = place_to_group_label(detected_place)
    target_group = place_to_group_label(target_place)

    # ---- plot ----
    plt.figure()
    plt.title(f"Articulation Position Check (target={target_group})")

    y0 = 0.0

    # 축 + 화살표 + 경계선 (같은 색)
    plt.annotate(
        "",
        xy=(3.15, y0), xytext=(-0.15, y0),
        arrowprops=dict(arrowstyle="->", linewidth=2, color=axis_color)
    )
    plt.vlines([1.0, 2.0], y0 - 0.08, y0 + 0.08, linewidth=2, color=axis_color)

    # x축 라벨
    plt.xticks([0.5, 1.5, 2.5], group_labels)
    plt.yticks([])

    # ★ 목표 (빨간색, 위쪽)
    if x_target is not None:
        plt.scatter([x_target], [y0], marker="*", s=300, color=target_color, zorder=5)
        plt.text(
            x_target, y0 + 0.20,
            "Target",
            ha="center", va="bottom",
            color=target_color,
            fontweight="bold"
        )

    # ▲ 사용자 (노란색, 아래쪽)
    plt.scatter([x_user], [y0], marker="^", s=280, color=user_color, zorder=6)
    plt.text(
        x_user, y0 - 0.22,
        "User",
        ha="center", va="top",
        color=user_color,
        fontweight="bold"
    )

    # 보기 좋게
    plt.ylim(-0.65, 0.65)
    plt.xlim(-0.2, 3.2)

    # ---------------------------
    # (B) VOT vs F0(z) - circle/ellipse reference clusters + syllable labels + user in yellow
    # ---------------------------

    plt.figure()

    # place에 따라 fortis/lenis/aspirated를 음절 라벨로 바꿈
    target_place = targets.get("place", None)
    label_map = phonation_to_syllable_labels(target_place)

    target_phon = targets.get("phonation", None)                 # fortis/lenis/aspirated
    target_phon_label = label_map.get(target_phon, target_phon)  # fortis -> 빠

    plt.title(f"Pronunciation Type Check (target={target_phon_label})")
    plt.xlabel("VOT (ms)")
    plt.ylabel("F0 z-score")


    # 축 범위(원하면 고정)
    plt.xlim(-5, 105)
    plt.ylim(-1.5, 4.5)

        # --- reference "타원" 클러스터 생성 (채우기) ---
    theta = np.linspace(0, 2*np.pi, 120)

    target_phon = targets.get("phonation", None)  # "fortis" / "lenis" / "aspirated"

    target_fill = "#d62728"  
    other_fill  = "#bcdff5" # 연한 파란색 (others)
    #edge_color  = "#666666"  # 테두리(너무 진하지 않게)

    for phon in ["fortis", "lenis", "aspirated"]:
        if phon not in vot_ranges or phon not in f0z_targets:
            continue

        lo, hi = vot_ranges[phon]["low"], vot_ranges[phon]["high"]
        xc = float(vot_ranges[phon]["center"])
        yc = float(f0z_targets[phon]["center"])

        xr = (hi - lo) / 2.0
        yr = float(f0z_targets[phon]["tol"])

        xs = xc + xr * np.cos(theta)
        ys = yc + yr * np.sin(theta)

        is_target = (phon == target_phon)

        # ✅ 채우기: target=연파랑, others=연회색
        face = target_fill if is_target else other_fill
        alpha = 0.55 if is_target else 0.35

        plt.fill(xs, ys, facecolor=face, alpha=alpha)
        # 그룹 라벨(음절) - center에 표시
        plt.text(xc, yc, f"{label_map.get(phon, phon)}", va="center", ha="center")

    # --- user point (노란색) ---
    ux = vot_point.get("x_vot_ms", None)
    uy = vot_point.get("y_f0_z", None)

    if ux is not None and uy is not None:
        # ✅ 검정 테두리 제거: edgecolors 제거, linewidth=0
        plt.scatter([ux], [uy], s=160, color="#ffbf00", zorder=10)

        # 사용자 분류 텍스트는 유지(원하면 이것도 스타일 바꿀 수 있음)
        pred_phon, dist = classify_by_reference_ellipse(ux, uy, vot_ranges, f0z_targets)
        # ✅ 사용자 문구를 점 바로 위에 노란색으로 표시
        plt.text(ux, uy + 0.3, f"User: {label_map.get(pred_phon, pred_phon)}", ha="center", va="bottom",
                 color="#ffbf00", fontweight="bold")

        # ✅ 측정값 텍스트 삭제 (기존 (20.5 ms, 2.22 z) 같은거 안 씀)

    else:
        if ux is not None:
            plt.scatter([ux], [0.0], s=160, color="#ffbf00", zorder=10)
            plt.text(ux, 0.12, "사용자", ha="center", va="bottom",
                     color="#ffbf00", fontweight="bold")
            plt.text(
                0.4, 0.95,
                "사용자: F0z가 없어 분류 불가",
                transform=plt.gca().transAxes,
                ha="left", va="top"
            )

    # 저장 옵션
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        plt.figure(1)
        plt.savefig(out_dir / f"{syllable}_f2.png", dpi=160, bbox_inches="tight")
        plt.figure(2)
        plt.savefig(out_dir / f"{syllable}_vot_f0z.png", dpi=160, bbox_inches="tight")

    #if show:
        #plt.show()
    #else:
    plt.close("all")


if __name__ == "__main__":
    # 사용 예:
    # python analysis/debug_stop_plot.py /path/to/카.wav 카
    wav_path = sys.argv[1]
    syllable = sys.argv[2]

    # F0z 보려면 calibration을 넣어야 y축 값이 생김
    # (대충 디버그용으로 평균/표준편차를 넣어도 되고, DB에서 가져오는 값을 넣어도 됨)
    calib = F0Calibration(mean_hz=180.0, sd_hz=30.0)  # 임시값

    res = analyze_stop(wav_path=wav_path, syllable=syllable, f0_calibration=calib)
    plot_stop_debug(res, out_dir=Path("debug_plots"), show=True)
    print(json.dumps(res, indent=2, ensure_ascii=False))