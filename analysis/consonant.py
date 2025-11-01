import os
import math
import argparse
import numpy as np
import scipy.signal
import parselmouth  # <- Praat bridge

############################################################
# 1. Reference data (same as yours)
############################################################

reference = {
    "다": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (62.9, 27.6),
                "female": (65.2, 23.1),
            },
            "asp_ratio": {
                "male":   (0.16, 0.06),
                "female": (0.18, 0.06),
            },
        },
        "coaching": "혀끝을 윗잇몸 바로 뒤에 대고 막았다가 부드럽게 떼면서 바로 소리를 내요. 숨을 세게 내뿜지 않아요. 성대 진동이 빨리 시작돼요."
    },
    "따": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (8.9, 4.2),
                "female": (9.8, 9.8),
            },
            "asp_ratio": {
                "male":   (0.07, 0.03),
                "female": (0.08, 0.03),
            },
        },
        "coaching": "혀는 단단하게 막고, 터뜨릴 때 거의 숨을 안 뿜어요. 대신 순간적으로 팍, 끊어지게 강하게 시작하세요."
    },
    "타": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (73.2, 20.5),
                "female": (72.0, 27.0),
            },
            "asp_ratio": {
                "male":   (0.38, 0.10),
                "female": (0.40, 0.10),
            },
        },
        "coaching": "혀를 떼고 바람(거친 숨소리)이 먼저 충분히 나오고, 그 다음에 목소리가 붙어요. 바람이 들려야 해요."
    },

    "가": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (67.1, 21.4),
                "female": (73.7, 22.5),
            },
            "asp_ratio": {
                "male":   (0.18, 0.06),
                "female": (0.20, 0.06),
            },
        },
        "coaching": "혀 뒷부분을 막았다가 떼면서 바로 소리를 시작해요. 너무 세게 숨을 뿜지 말고 부드럽게 '가'."
    },
    "까": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (15.9, 9.0),
                "female": (12.5, 8.6),
            },
            "asp_ratio": {
                "male":   (0.09, 0.04),
                "female": (0.10, 0.04),
            },
        },
        "coaching": "혀 뒷부분을 단단하게 붙였다가 딱 떼요. 숨 거의 없이 바로 소리가 붙어요. 짧고 강하게."
    },
    "카": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (73.4, 28.3),
                "female": (81.8, 24.1),
            },
            "asp_ratio": {
                "male":   (0.40, 0.10),
                "female": (0.42, 0.10),
            },
        },
        "coaching": "막고 있다가 떼고 나서, 거친 숨(ㅋ) 소리가 먼저 길게 나오고, 그 다음에 목소리가 붙어요."
    },

    "바": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (59.6, 24.0),
                "female": (62.5, 22.9),
            },
            "asp_ratio": {
                "male":   (0.08, 0.05),
                "female": (0.08, 0.05),
            },
        },
        "coaching": "입술을 붙였다가 부드럽게 떼면서 바로 울림이 나요. 숨을 세게 '푸'하고 내보내지 마세요. 거의 바로 '바'처럼 들려야 해요."
    },
    "빠": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (7.7, 4.0),
                "female": (6.2, 4.5),
            },
            "asp_ratio": {
                "male":   (0.05, 0.03),
                "female": (0.05, 0.03),
            },
        },
        "coaching": "입술을 꽉 막았다가 짧게 '빡' 터뜨리듯이. 숨 거의 없이, 바로 소리. 단단하고 묵직하게."
    },
    "파": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (67.4, 27.0),
                "female": (74.3, 28.9),
            },
            "asp_ratio": {
                "male":   (0.42, 0.10),
                "female": (0.45, 0.10),
            },
        },
        "coaching": "입술을 떼고 바람을 확 내보낸 다음 한 박자 뒤에 목소리가 들어와요. '파'는 바람이 들려야 해요."
    },

    "사": {
        "type": "fricative",
        "features": {
            "fric_dur_ms": {
                "male":   (110, 15),
                "female": (100, 15),
            },
            "centroid_kHz": {
                "male":   (6.5, 0.5),
                "female": (7.2, 0.5),
            },
        },
        "coaching": "혀끝을 치아/치조 근처로 가까이 두고 'ssss' 마찰을 유지하다가 바로 '아'로 넘어가요. 부드럽게, 너무 조이지 않게."
    },
    "싸": {
        "type": "fricative",
        "features": {
            "fric_dur_ms": {
                "male":   (90, 10),
                "female": (85, 10),
            },
            "centroid_kHz": {
                "male":   (8.5, 0.5),
                "female": (9.2, 0.6),
            },
        },
        "coaching": "‘싸’는 더 세고 날카로운 치- 소리예요. 짧고 강하고 높은 주파수. 혀를 더 조여서 내세요."
    },
    "하": {
        "type": "fricative",
        "features": {
            "fric_dur_ms": {
                "male":   (120, 15),
                "female": (130, 15),
            },
            "centroid_kHz": {
                "male":   (4.0, 0.5),
                "female": (4.0, 0.5),
            },
        },
        "coaching": "목구멍 쪽에서 숨이 먼저 'hhh'처럼 퍼지게 새고 그 다음 '아'. 예리한 치- 소리보다 훨씬 퍼진 바람 소리."
    },

    "자": {
        "type": "affricate",
        "features": {
            "VOT_ms": {
                "male":   (30, 6),
                "female": (40, 6),
            },
            "fric_dur_ms": {
                "male":   (80, 10),
                "female": (75, 10),
            },
        },
        "coaching": "막았다가 터뜨리면서 바로 치- 마찰이 나오고 '아'로 넘어가요. 부드럽지만 분명하게."
    },
    "짜": {
        "type": "affricate",
        "features": {
            "VOT_ms": {
                "male":   (10, 4),
                "female": (12, 4),
            },
            "fric_dur_ms": {
                "male":   (65, 10),
                "female": (60, 10),
            },
        },
        "coaching": "‘짜’는 아주 단단하고 짧게 '쨌!'처럼 터져요. 숨을 많이 안 새게 하고 압축된 느낌."
    },
    "차": {
        "type": "affricate",
        "features": {
            "VOT_ms": {
                "male":   (85, 12),
                "female": (95, 12),
            },
            "fric_dur_ms": {
                "male":   (100, 15),
                "female": (95, 15),
            },
        },
        "coaching": "‘차’는 터뜨린 다음 거친 치- 마찰이 들리고 나서 모음 '아'가 와요. 즉, 바람 먼저."
    },

    "마": {
        "type": "sonorant",
        "features": {
            "seg_dur_ms": {
                "male":   (80, 15),
                "female": (85, 15),
            },
            "nasal_lowFreq_amp": {
                "male":   (1.0, 0.2),
                "female": (1.0, 0.2),
            },
        },
        "coaching": "입술을 닫고 코로 'mmmm…' 울리다가 바로 '아'. 소리는 코에서 울려야 해요."
    },
    "나": {
        "type": "sonorant",
        "features": {
            "seg_dur_ms": {
                "male":   (80, 15),
                "female": (85, 15),
            },
            "nasal_lowFreq_amp": {
                "male":   (1.0, 0.2),
                "female": (1.0, 0.2),
            },
        },
        "coaching": "혀끝을 윗잇몸 뒤에 붙이고 'nnnn…' 콧울림을 유지하다가 '아'. 콧소리가 계속 살아 있어야 해요."
    },
    "라": {
        "type": "sonorant",
        "features": {
            "seg_dur_ms": {
                "male":   (35, 5),
                "female": (40, 5),
            },
            "nasal_lowFreq_amp": {
                "male":   (0.5, 0.1),
                "female": (0.5, 0.1),
            },
        },
        "coaching": "혀끝을 가볍게 치고 짧게 'ㄹ'만 튕기고 바로 '아'. 길게 늘어뜨리지 마세요."
    },
}

############################################################
# 2. Utility helpers
############################################################

def load_sound(path):
    """
    Return: snd (parselmouth.Sound), y (numpy float64), sr (int)
    """
    snd = parselmouth.Sound(path)
    y = snd.values.T.flatten().astype(np.float64)  # Praat gives [channels x samples], we flatten mono
    sr = int(round(snd.sampling_frequency))
    return snd, y, sr

def bandpass(sig, sr, low, high, order=4):
    nyq = sr / 2.0
    lo = max(low / nyq, 0.0001)
    hi = min(high / nyq, 0.9999)
    b, a = scipy.signal.butter(order, [lo, hi], btype='band')
    return scipy.signal.lfilter(b, a, sig)

def lowpass(sig, sr, cutoff, order=4):
    nyq = sr / 2.0
    norm_cut = cutoff / nyq
    b, a = scipy.signal.butter(order, norm_cut, btype='low')
    return scipy.signal.lfilter(b, a, sig)

############################################################
# 3. Burst detection (parselmouth-friendly)
############################################################

def detect_burst_time(snd):
    """
    Burst time estimate using Praat Intensity.
    We pick the first frame whose intensity is within ~30 dB of max.
    If nothing qualifies, fallback to first frame.

    Returns burst_time (sec)
    """
    intensity = snd.to_intensity(minimum_pitch=100.0)
    int_vals = intensity.values[0]  # shape (n_frames,)
    int_max = np.max(int_vals)
    burst_cands = np.where(int_vals > (int_max - 30))[0]

    if burst_cands.size == 0:
        burst_time = intensity.get_time_from_frame_number(1)
        if burst_time < 0:
            burst_time = 0.0
    else:
        first_burst_frame = int(burst_cands[0])
        burst_time = intensity.get_time_from_frame_number(first_burst_frame + 1)

    return float(burst_time)

############################################################
# 4. Helper: which sounds are aspirated-like?
############################################################

def is_aspirated_like(syllable):
    # strongly aspirated release -> long VOT expected
    # include aspirated stops and aspirated affricate
    return syllable in ["파", "타", "카", "차"]

############################################################
# 5. Voiced onset after burst, adaptive VOT_ms
############################################################

def estimate_vot_ms(snd, aspirated_mode=False):
    """
    Returns (vot_ms, burst_t, voiced_t).

    aspirated_mode:
        True  -> stricter voiced onset (파/타/카/차),
                 we want clear vowel after noisy puff
        False -> looser (바/빠/다/따/가/까...), allow weak early voicing
    """

    sr = snd.sampling_frequency
    burst_t = detect_burst_time(snd)

    # analyze only ~120 ms after burst
    end_t = min(burst_t + 0.18, snd.xmax)
    snd_after = snd.extract_part(from_time=burst_t, to_time=end_t, preserve_times=False)

    # pitch estimation (Praat)
    pitch = snd_after.to_pitch(time_step=0.001)
    pitch_values = pitch.selected_array["frequency"]  # Hz, 0 if unvoiced
    pitch_times = np.array([
        pitch.get_time_from_frame_number(i+1) for i in range(len(pitch_values))
    ])

    # harmonicity (HNR)
    harm = snd_after.to_harmonicity_cc(time_step=0.001)
    harm_vals = harm.values[0]  # dB HNR
    harm_times = np.array([
        harm.get_time_from_frame_number(i+1) for i in range(len(harm_vals))
    ])

    # intensity of slice
    intensity_local = snd_after.to_intensity(minimum_pitch=100.0)
    int_vals_local = intensity_local.values[0]
    int_times_local = np.array([
        intensity_local.get_time_from_frame_number(i+1)
        for i in range(len(int_vals_local))
    ])
    local_int_max = np.max(int_vals_local) if len(int_vals_local) > 0 else -200.0

    voiced_t_rel = None

    for i in range(len(pitch_values)):
        f0 = pitch_values[i]
        if f0 <= 70 or f0 >= 400:
            continue  # reject too low/high or unvoiced (0)

        t_candidate = pitch_times[i]

        # nearest harmonicity frame
        if len(harm_times) > 0:
            h_i = np.argmin(np.abs(harm_times - t_candidate))
            hnr_db = harm_vals[h_i]
        else:
            hnr_db = -100.0

        # nearest intensity frame
        if len(int_times_local) > 0:
            ii = np.argmin(np.abs(int_times_local - t_candidate))
            this_int = int_vals_local[ii]
        else:
            this_int = -200.0

        if aspirated_mode:
            # strict: need clearly periodic voiced vowel after aspirated noise
            if (hnr_db > 5.0) and (this_int > (local_int_max - 40.0)):
                voiced_t_rel = t_candidate
                break
        else:
            # lenis/fortis style: allow weaker/creaky onset
            if this_int > (local_int_max - 50.0):
                voiced_t_rel = t_candidate
                break

    if voiced_t_rel is None:
        # backup: use ANY plausible pitch frame (ignoring intensity/HNR),
        # because this might be a lenis with near-zero VOT.
        loose_idx = np.where((pitch_values > 70) & (pitch_values < 400))[0]
        if loose_idx.size > 0:
            voiced_t_rel = pitch_times[loose_idx[0]]
        else:
            # truly no voicing detected in window
            return (None, burst_t, None)

    voiced_t = burst_t + voiced_t_rel
    vot_ms = (voiced_t - burst_t) * 1000.0
    if vot_ms < 0:
        vot_ms = 0.0

    return (float(vot_ms), float(burst_t), float(voiced_t))

############################################################
# 6. Aspiration ratio
############################################################

def aspiration_ratio_after_burst(y, sr, burst_t, voiced_t,
                                 fallback_asp_dur_ms=80,
                                 total_win_ms=300,
                                 high_band=(4000,8000)):
    """
    After we know burst_t and voiced_t, measure how 'hissy/aspirated' it is.
    """

    if burst_t is None:
        return None

    if voiced_t is None:
        asp_start_t = burst_t
        asp_end_t   = burst_t + (fallback_asp_dur_ms/1000.0)
    else:
        asp_start_t = burst_t
        asp_end_t   = voiced_t

    if asp_end_t <= asp_start_t:
        return 0.0

    asp_start_i = int(asp_start_t * sr)
    asp_end_i   = int(min(len(y), asp_end_t * sr))

    if asp_end_i - asp_start_i < int(0.01 * sr):  # <10 ms
        return 0.0

    aspiration_seg = y[asp_start_i:asp_end_i]

    total_start_t = burst_t
    total_end_t   = burst_t + (total_win_ms/1000.0)
    total_start_i = int(total_start_t * sr)
    total_end_i   = int(min(len(y), total_end_t * sr))

    total_seg = y[total_start_i:total_end_i]

    total_rms = np.sqrt(np.mean(total_seg**2) + 1e-12)

    hi = bandpass(aspiration_seg, sr, high_band[0], high_band[1])
    hi_rms = np.sqrt(np.mean(hi**2) + 1e-12)

    if total_rms < 1e-9:
        return 0.0

    return float(hi_rms / total_rms)

############################################################
# 7. Burst loudness diagnostic
############################################################

def burst_energy_db(y, sr, burst_t, win_ms=8.0):
    if burst_t is None:
        return None
    start = int(burst_t * sr)
    end = int(start + (win_ms / 1000.0) * sr)
    end = min(end, len(y))
    if end - start < 4:
        return None
    seg = y[start:end]
    rms = np.sqrt(np.mean(seg**2) + 1e-12)
    burst_db = 20.0 * np.log10(rms + 1e-12)
    return float(burst_db)

############################################################
# 8. Pitch + inferred sex (UPDATED)
############################################################

def estimate_speaker_f0_and_sex(wav_path, vot_ms=None, extra_offset_ms=10,
                                pitch_floor=75, pitch_ceiling=500):
    """
    Extract median f0 (Hz) from the vowel portion after the consonant.
    We skip the burst / aspiration part so pitch tracker actually sees voicing.

    wav_path: path to the wav file
    vot_ms:   voice onset time in ms that we already measured
    extra_offset_ms: analyze starting a little after VOT to be safely in vowel
    returns: (f0_median_hz or None, inferred_sex_str)
    """

    snd_full = parselmouth.Sound(wav_path)

    # pick start time for vowel analysis
    if vot_ms is None:
        start_t = 0.0
    else:
        start_t = (vot_ms + extra_offset_ms) / 1000.0

    total_dur = snd_full.get_total_duration()
    if start_t >= total_dur:
        start_t = 0.0

    snd_crop = snd_full.extract_part(
        from_time=start_t,
        to_time=total_dur,
        preserve_times=False
    )

    pitch = snd_crop.to_pitch(
        time_step=0.01,
        pitch_floor=pitch_floor,
        pitch_ceiling=pitch_ceiling
    )
    f0_values = pitch.selected_array['frequency']  # Hz
    voiced_f0 = f0_values[f0_values > 0]

    if voiced_f0.size == 0:
        # no voiced pitch found at all
        return None, "unknown"

    f0_median = float(np.median(voiced_f0))

    # infer sex from pitch
    # ~<165 Hz => likely male, ~>=165 Hz => likely female
    if f0_median >= 165:
        inferred_sex = "female"
    else:
        inferred_sex = "male"

    return f0_median, inferred_sex

############################################################
# 9. Fricatives + affricates timing and centroid
############################################################

def compute_spectral_centroid(signal, sr, n_fft=1024, hop=256):
    """
    Manual centroid in Hz.
    """
    win = np.hanning(n_fft)

    cents = []
    times = []

    for start in range(0, len(signal) - n_fft, hop):
        frame = signal[start:start+n_fft] * win

        spec = np.abs(np.fft.rfft(frame))
        freqs = np.fft.rfftfreq(n_fft, d=1.0/sr)

        mag_sum = np.sum(spec) + 1e-12
        centroid_hz = float(np.sum(freqs * spec) / mag_sum)

        frame_center_t = (start + n_fft / 2.0) / sr
        cents.append(centroid_hz)
        times.append(frame_center_t)

    if len(times) == 0:
        return np.array([]), np.array([])

    return np.array(times), np.array(cents)

def frication_stats(snd, y, sr,
                    soft_cap_ms=150.0,
                    intensity_floor_db_from_peak=30.0,
                    min_pitch_hz=70.0,
                    max_pitch_hz=400.0):
    """
    Measure frication duration and centroid before first vowel-ish onset.

    Returns:
        fric_dur_ms (float or None),
        centroid_kHz (float or None),
        confident (bool)
    """

    # --- 1. pitch-based vowel onset ---
    pitch = snd.to_pitch(time_step=0.001)
    p_vals = pitch.selected_array["frequency"]  # Hz, 0 if unvoiced
    p_times = np.array([
        pitch.get_time_from_frame_number(i+1)
        for i in range(len(p_vals))
    ])

    voiced_idx = np.where((p_vals > min_pitch_hz) & (p_vals < max_pitch_hz))[0]
    if voiced_idx.size > 0:
        onset_pitch = p_times[voiced_idx[0]]
    else:
        onset_pitch = None

    # --- 2. intensity-based vowel onset (fallback, looser than before) ---
    intensity_obj = snd.to_intensity(minimum_pitch=100.0)
    int_vals = intensity_obj.values[0]  # dB
    int_times = np.array([
        intensity_obj.get_time_from_frame_number(i+1)
        for i in range(len(int_vals))
    ])

    if len(int_vals) > 0:
        peak_int = np.max(int_vals)
        # "vowel-like" = within 30 dB of peak (was 20 dB, now looser)
        loud_frames = np.where(int_vals > (peak_int - intensity_floor_db_from_peak))[0]
        if loud_frames.size > 0:
            onset_intensity = int_times[loud_frames[0]]
        else:
            onset_intensity = None
    else:
        onset_intensity = None

    # --- 3. choose earliest plausible onset ---
    onset_candidates = []
    if onset_pitch is not None:
        onset_candidates.append(onset_pitch)
    if onset_intensity is not None:
        onset_candidates.append(onset_intensity)

    if len(onset_candidates) > 0:
        first_voiced_time = min(onset_candidates)
    else:
        first_voiced_time = None  # we basically failed

    # --- 4. define frication window ---
    fric_start_t = snd.xmin

    if first_voiced_time is not None:
        raw_dur_ms = (first_voiced_time - fric_start_t) * 1000.0
        if raw_dur_ms < 0:
            raw_dur_ms = 0.0
    else:
        # we didn't detect vowel onset confidently
        raw_dur_ms = soft_cap_ms + 1.0  # force "too long"

    # --- 5. confidence & clamping ---
    # if raw duration is longer than soft_cap_ms, we don't trust it
    if raw_dur_ms > soft_cap_ms:
        confident = False
        fric_dur_ms = soft_cap_ms  # clip for centroid calc
    else:
        confident = True
        fric_dur_ms = raw_dur_ms

    # --- 6. extract just that frication slice for centroid ---
    fric_end_t = fric_start_t + (fric_dur_ms / 1000.0)
    fric_seg = snd.extract_part(
        from_time=fric_start_t,
        to_time=fric_end_t,
        preserve_times=False
    )
    y_fric = fric_seg.values.T.flatten().astype(np.float64)

    t_arr, cents_hz = compute_spectral_centroid(y_fric, sr)

    if cents_hz.size == 0:
        centroid_kHz = None
    else:
        centroid_kHz = float(np.mean(cents_hz) / 1000.0)

    # if we weren't confident, don't trust the numbers for scoring
    if not confident:
        return None, None, False

    return fric_dur_ms, centroid_kHz, True

############################################################
# 10. Sonorant timing + nasal energy
############################################################

def segment_duration_ms(snd):
    """
    How long until first stable voicing (in ms).
    For nasals/liquids we interpret that as consonant duration before vowel.
    """
    pitch = snd.to_pitch(time_step=0.001)
    p_vals = pitch.selected_array["frequency"]
    p_times = np.array([
        pitch.get_time_from_frame_number(i+1) for i in range(len(p_vals))
    ])
    voiced_idx = np.where(p_vals > 0)[0]

    if voiced_idx.size > 0:
        first_voiced_t = p_times[voiced_idx[0]]
    else:
        first_voiced_t = snd.xmax

    return (first_voiced_t - snd.xmin) * 1000.0

def lowfreq_ratio(y, sr, cutoff=500.0):
    """
    nasal_lowFreq_amp ~ how strong low freq energy is relative to total.
    """
    low = lowpass(y, sr, cutoff)
    total_rms = np.sqrt(np.mean(y**2) + 1e-12)
    low_rms   = np.sqrt(np.mean(low**2) + 1e-12)
    return float(low_rms / total_rms)

############################################################
# 11. Scoring / z-score logic
############################################################

def raw_z_score(value, mean, sd):
    if value is None or sd == 0:
        return None
    return (value - mean) / sd

def capped_z(value, mean, sd, cap=3.0):
    z = raw_z_score(value, mean, sd)
    if z is None:
        return None
    if z > cap:
        return cap
    if z < -cap:
        return -cap
    return z

def score_against_reference(measured_feats, ref_feats, sex):
    per_feature_report = {}
    z_list = []
    advice_list = []

    for feat_name, per_sex_stats in ref_feats.items():
        if sex not in per_sex_stats:
            continue
        mean, sd = per_sex_stats[sex]
        measured_val = measured_feats.get(feat_name, None)
        z = capped_z(measured_val, mean, sd)

        per_feature_report[feat_name] = {
            "target_mean": mean,
            "target_sd": sd,
            "your_value": measured_val,
            "z_score": z,
        }

        if z is not None:
            z_list.append(abs(z))

            if abs(z) <= 1.0:
                advice_list.append(f"{feat_name}: good, close to native range.")
            else:
                direction = "higher" if measured_val > mean else "lower"

                if feat_name == "VOT_ms":
                    if measured_val is None:
                        advice_list.append("Could not detect VOT cleanly. Try a clearer burst then vowel.")
                    elif measured_val > mean:
                        advice_list.append("Your VOT is long → you're waiting too long to start voicing. Try starting voice sooner.")
                    else:
                        advice_list.append("Your VOT is very short → you're starting voice too fast. Loosen a bit.")

                elif feat_name == "asp_ratio":
                    if measured_val is None:
                        advice_list.append("Aspiration window unclear. Try making the '파/카/타' burst more breathy and clear.")
                    elif measured_val > mean:
                        advice_list.append("Strong high-frequency breath noise (very aspirated). Try reducing the burst of air.")
                    else:
                        advice_list.append("Very low aspiration/noise. If this is supposed to be aspirated, add more breathy release.")

                elif feat_name == "fric_dur_ms":
                    advice_list.append("Your frication length is " + direction + " than typical. Match how long you hold the hiss before the vowel.")

                elif feat_name == "centroid_kHz":
                    advice_list.append("Your hiss energy peak is " + direction + " than typical. Tongue groove/pressure might differ.")

                elif feat_name == "seg_dur_ms":
                    advice_list.append("Your consonant duration before voicing is " + direction + " than native. Control how fast you release into the vowel.")

                elif feat_name == "nasal_lowFreq_amp":
                    advice_list.append("Your low-frequency nasal energy is " + direction + " than expected. Check nasal/oral airflow balance.")

    if len(z_list) == 0:
        overall_score = None
    else:
        avg_abs_z = sum(z_list)/len(z_list)
        overall_score = max(0, 100 - (avg_abs_z * 20))

    return per_feature_report, overall_score, advice_list

############################################################
# 12. Feature extraction dispatcher
############################################################

def extract_features_for_syllable(snd, y, sr, syllable_label, syllable_info):
    ctype = syllable_info["type"]
    feats = {}

    # decide if we should use strict (aspirated) or loose (lenis/fortis) VOT detection
    aspirated_mode = False
    if ctype in ["stop", "affricate"] and is_aspirated_like(syllable_label):
        aspirated_mode = True

    if ctype == "stop":
        vot_ms, burst_t, voiced_t = estimate_vot_ms(snd, aspirated_mode=aspirated_mode)
        feats["VOT_ms"] = vot_ms
        feats["asp_ratio"] = aspiration_ratio_after_burst(y, sr, burst_t, voiced_t)
        feats["burst_dB"] = burst_energy_db(y, sr, burst_t)

    elif ctype == "affricate":
        vot_ms, burst_t, voiced_t = estimate_vot_ms(snd, aspirated_mode=aspirated_mode)
        fric_dur_ms, centroid_kHz, confident = frication_stats(snd, y, sr)
        feats["VOT_ms"] = vot_ms

        if confident:
            feats["fric_dur_ms"] = fric_dur_ms
            feats["centroid_kHz"] = centroid_kHz
        else:
            feats["fric_dur_ms"] = None
            feats["centroid_kHz"] = None


    elif ctype == "fricative":
        fric_dur_ms, centroid_kHz, confident = frication_stats(snd, y, sr)

        if confident:
            feats["fric_dur_ms"] = fric_dur_ms
            feats["centroid_kHz"] = centroid_kHz
        else:
            # we failed to get a reliable segmentation — don't punish user
            feats["fric_dur_ms"] = None
            feats["centroid_kHz"] = None

    elif ctype == "sonorant":
        seg_dur = segment_duration_ms(snd)
        nasal_ratio = lowfreq_ratio(y, sr)
        feats["seg_dur_ms"] = seg_dur
        feats["nasal_lowFreq_amp"] = nasal_ratio

    return feats

############################################################
# 13. Main analysis for one file (UPDATED ORDER)
############################################################

def analyze_one_file(wav_path, syllable):
    """
    Run analysis for one (syllable, wav).
    We catch exceptions so batch scripts don't die mid-run.
    """

    if syllable not in reference:
        print("====================================================")
        print(f"Syllable: {syllable}")
        print(f"File: {wav_path}")
        print("[ERROR] This syllable is not in reference.")
        print("====================================================\n")
        return

    info = reference[syllable]

    try:
        # Load audio via parselmouth
        snd, y, sr = load_sound(wav_path)

        # 1. Extract acoustic features FIRST (we need VOT_ms for f0 cropping)
        measured_feats = extract_features_for_syllable(snd, y, sr, syllable, info)

        # Get VOT_ms if available (stops/affricates); else None
        vot_for_pitch = measured_feats.get("VOT_ms", None)

        # 2. Estimate speaker f0 and guess sex using vowel region after VOT
        f0_est, sex_guess = estimate_speaker_f0_and_sex(
            wav_path=wav_path,
            vot_ms=vot_for_pitch
        )
        sex_for_scoring = sex_guess if sex_guess != "unknown" else "female"

        # 3. Compare to reference
        per_feature_report, overall_score, advice_list = score_against_reference(
            measured_feats,
            info["features"],
            sex_for_scoring
        )

        # 4. Print report
        print("====================================================")
        print(f"Syllable: {syllable}")
        print(f"File: {wav_path}")
        print("How to pronounce:", info["coaching"])
        print()

        print(f"Inferred sex (by f0): {sex_guess}  [used for scoring: {sex_for_scoring}]")
        print(f"Estimated f0 (median voiced Hz): {f0_est}")
        print()

        print("=== Feature Comparison (scored) ===")
        for feat_name, rep in per_feature_report.items():
            print(f"- {feat_name}:")
            print(f"    your_value       = {rep['your_value']}")
            print(f"    target_mean      = {rep['target_mean']} ({sex_for_scoring})")
            print(f"    target_sd        = {rep['target_sd']}")
            print(f"    z_score          = {rep['z_score']}")
        print()

        if "burst_dB" in measured_feats:
            print("=== Extra Acoustic Diagnostics (not scored) ===")
            print(f"- burst_dB (release pop loudness): {measured_feats['burst_dB']}")
            print()

        print("=== Overall Score (0-100, higher = closer to native) ===")
        print(overall_score)
        print()

        print("=== Feedback ===")
        if advice_list:
            for a in advice_list:
                print("•", a)
        else:
            print("• Sounds within native-like range.")
        print()

        print("Extra articulation coaching for", syllable, ":")
        print(info["coaching"])
        print("====================================================\n")

    except Exception as e:
        print("====================================================")
        print(f"Syllable: {syllable}")
        print(f"File: {wav_path}")
        print("[ERROR DURING ANALYSIS]")
        print(f"{type(e).__name__}: {e}")
        print()
        print("Tip: This usually happens if the file is too short or mostly silence,")
        print("or if frication/pitch couldn't be measured.")
        print("====================================================\n")

############################################################
# 14. CLI main()
############################################################

def main():
    parser = argparse.ArgumentParser(
        description="Analyze one consonant+ㅏ recording and print the feedback report."
    )
    parser.add_argument(
        "--syllable",
        required=True,
        help="Target syllable label, e.g. '다', '까', '파', '나' (must exist in reference)."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the .wav file for that syllable."
    )

    args = parser.parse_args()
    analyze_one_file(args.file, args.syllable)

if __name__ == "__main__":
    main()
