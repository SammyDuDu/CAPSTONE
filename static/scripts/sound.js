// 음성 녹음 후 FastAPI 분석 엔진과 통신
// Record audio and send to FastAPI analysis engine
(function () {
    const RECORDING_DURATION_MS = 1000;  // 1 second for monophthongs
    const DIPHTHONG_DURATION_MS = 1500;  // 1.5 seconds for diphthongs

    // True diphthongs that need trajectory analysis (w-glide vowels)
    // Y-vowels (ㅑ,ㅕ,ㅛ,ㅠ,ㅒ,ㅖ) are treated as monophthongs (short glide + vowel)
    const DIPHTHONG_SYMBOLS = ['ㅘ', 'ㅙ', 'ㅚ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅢ'];

    function isDiphthong(symbol) {
        return DIPHTHONG_SYMBOLS.includes(symbol);
    }

    function getRecordingDuration(symbol) {
        return isDiphthong(symbol) ? DIPHTHONG_DURATION_MS : RECORDING_DURATION_MS;
    }
    const btn = document.getElementById('recordBtn');
    if (!btn) return;

    const percentEl = document.querySelector('.card.total .percent');
    const statusEl = document.getElementById('analysisStatus');
    const feedbackEl = document.getElementById('analysisFeedback');
    const soundSymbolEl = document.getElementById('soundSymbol');
    const cards = Array.from(document.querySelectorAll('.card[data-feature]'));
    const plotContainer = document.getElementById('analysisPlot');
    const plotCaption = document.getElementById('analysisPlotCaption');

    // Initialize DualPlotRenderer for side-by-side display
    let dualPlotRenderer = null;
    const formantCanvas = document.getElementById('formantCanvas');
    const articulatoryCanvas = document.getElementById('articulatoryCanvas');

    if (formantCanvas && articulatoryCanvas) {
        dualPlotRenderer = new DualPlotRenderer('formantCanvas', 'articulatoryCanvas');
        console.log('[sound.js] DualPlotRenderer initialized');

        // Load calibration data if logged in
        const userid = parseInt(sessionStorage.getItem('userid') || '0', 10);
        if (userid > 0) {
            loadCalibrationData(userid);
        } else {
            // Load standard reference vowels for guests
            loadStandardReferenceVowels();
        }
    }

    // Load calibration data and apply to renderer
    async function loadCalibrationData(userid) {
        try {
            const response = await fetch(`/api/formants?userid=${userid}`);
            if (!response.ok) {
                loadStandardReferenceVowels();
                return;
            }

            const data = await response.json();
            const formants = data.formants || {};
            const affineTransform = data.affine_transform;

            console.log('[sound.js] Loaded calibration data:', formants);

            // Apply Affine transform if available
            if (affineTransform && affineTransform.A && affineTransform.b && dualPlotRenderer) {
                dualPlotRenderer.setAffineTransform(affineTransform.A, affineTransform.b);
            }

            // Set calibration points
            const calibrationPoints = [];
            const labelMap = { 'a': 'ㅏ', 'i': 'ㅣ', 'u': 'ㅜ', 'eo': 'ㅓ', 'e': 'ㅔ' };

            for (const [sound, calib] of Object.entries(formants)) {
                if (calib.f1_mean && calib.f2_mean) {
                    calibrationPoints.push({
                        f1: calib.f1_mean,
                        f2: calib.f2_mean,
                        f1_sd: calib.f1_std || 50,
                        f2_sd: calib.f2_std || 80,
                        label: labelMap[sound] || sound
                    });
                }
            }

            if (calibrationPoints.length > 0 && dualPlotRenderer) {
                dualPlotRenderer.setCalibrationPoints(calibrationPoints);
                console.log('[sound.js] Calibration points set:', calibrationPoints.length);
            }

            // Load standard reference vowels
            loadStandardReferenceVowels();
        } catch (error) {
            console.error('[sound.js] Failed to load calibration data:', error);
            loadStandardReferenceVowels();
        }
    }

    // Load standard reference vowels with SD values
    function loadStandardReferenceVowels() {
        // Korean vowels with F1, F2, and standard deviations (Female reference)
        const standardVowels = [
            { f1: 945, f2: 1582, f1_sd: 83, f2_sd: 141, label: 'ㅏ' },
            { f1: 317, f2: 2780, f1_sd: 22, f2_sd: 109, label: 'ㅣ' },
            { f1: 417, f2: 1217, f1_sd: 54, f2_sd: 139, label: 'ㅡ' },
            { f1: 615, f2: 1096, f1_sd: 63, f2_sd: 99, label: 'ㅓ' },
            { f1: 453, f2: 947, f1_sd: 63, f2_sd: 124, label: 'ㅗ' },
            { f1: 389, f2: 1206, f1_sd: 53, f2_sd: 183, label: 'ㅜ' },
            { f1: 657, f2: 2261, f1_sd: 85, f2_sd: 133, label: 'ㅐ' },
            { f1: 525, f2: 2277, f1_sd: 82, f2_sd: 149, label: 'ㅔ' },
            { f1: 825, f2: 1757, f1_sd: 78, f2_sd: 176, label: 'ㅑ' },
            { f1: 485, f2: 1206, f1_sd: 70, f2_sd: 168, label: 'ㅕ' },
            { f1: 395, f2: 860, f1_sd: 54, f2_sd: 115, label: 'ㅛ' },
            { f1: 351, f2: 1437, f1_sd: 42, f2_sd: 227, label: 'ㅠ' }
        ];

        if (dualPlotRenderer) {
            dualPlotRenderer.setReferenceVowels(standardVowels);
            console.log('[sound.js] Standard reference vowels set');
        }
    }

    const cardMap = new Map();
    const defaultCardState = {};
    cards.forEach(card => {
        const key = card.dataset.feature;
        if (!key) return;
        const titleEl = card.querySelector('.card-title');
        const bodyEl = card.querySelector('.card-body');
        cardMap.set(key, { card, titleEl, bodyEl });
        defaultCardState[key] = {
            title: titleEl ? titleEl.textContent || '' : '',
            body: bodyEl ? bodyEl.textContent || '' : '',
        };
    });

    const metricCardOrder = ['tongue-height', 'tongue-backness', 'lips-roundness', 'breathiness'];
    const consonantFeatureLabels = {
        VOT_ms: 'Voice Onset Time (ms)',
        asp_ratio: 'Aspiration Ratio',
        fric_dur_ms: 'Frication Length (ms)',
        centroid_kHz: 'Spectral Centroid (kHz)',
        seg_dur_ms: 'Segment Length (ms)',
        nasal_lowFreq_amp: 'Nasal Low Freq Ratio',
    };

    const resetPlot = () => {
        if (plotContainer) plotContainer.hidden = true;
        if (plotCaption) plotCaption.textContent = '';
        if (dualPlotRenderer) {
            dualPlotRenderer.clearTrajectories();
        }
    };

    const resetCards = () => {
        cardMap.forEach((entry, key) => {
            const defaults = defaultCardState[key] || {};
            if (entry.titleEl && typeof defaults.title === 'string') {
                entry.titleEl.textContent = defaults.title;
            }
            if (entry.bodyEl) {
                entry.bodyEl.textContent = defaults.body || '';
            }
        });
        resetPlot();
    };

    const setCard = (key, title, body) => {
        const entry = cardMap.get(key);
        if (!entry) return;
        if (title && entry.titleEl) {
            entry.titleEl.textContent = title;
        }
        if (entry.bodyEl) {
            entry.bodyEl.textContent = body || '';
        }
    };

    const formatNumber = (value, decimals = 0) => {
        if (typeof value !== 'number' || Number.isNaN(value)) return null;
        const factor = Math.pow(10, decimals);
        return Math.round(value * factor) / factor;
    };

    const describeMetric = (value, target, sd, { unit = '', decimals = 0 } = {}) => {
        const measured = formatNumber(value, decimals);
        if (measured === null) return 'Measurement unavailable (측정 불가)';

        const unitStr = unit ? ` ${unit}` : '';
        let text = `${measured}${unitStr}`;

        const hasTarget = typeof target === 'number' && !Number.isNaN(target);
        if (!hasTarget) {
            return text;
        }

        const targetVal = formatNumber(target, decimals);
        if (targetVal === null) {
            return text;
        }

        let diffVal = formatNumber(measured - targetVal, decimals);
        if (diffVal === null) {
            diffVal = measured - targetVal;
        }
        if (Object.is(diffVal, -0)) diffVal = 0;
        const diffStr = diffVal === 0 ? '0' : `${diffVal > 0 ? '+' : ''}${diffVal}`;

        text += ` (Target ${targetVal}${unitStr} (목표 ${targetVal}${unitStr})`;
        if (typeof sd === 'number' && !Number.isNaN(sd)) {
            const sdVal = formatNumber(sd, decimals);
            if (sdVal !== null) {
                text += ` ±${sdVal}${unitStr}`;
            }
        }
        text += `, Difference ${diffStr}${unitStr} (차이 ${diffStr}${unitStr}))`;
        return text;
    };

    const renderVowelCards = (data) => {
        const details = data.details || {};
        const formants = details.formants || {};
        const reference = details.reference || {};
        const qualityHint = details.quality_hint;
        const gender = details.gender;
        const isDiphthong = details.is_diphthong || false;

        if (isDiphthong && details.trajectory && details.scores) {
            const trajectory = details.trajectory || {};
            const scores = details.scores || {};
            console.log('[sound.js] Diphthong trajectory data:', JSON.stringify(trajectory, null, 2));
            console.log('[sound.js] Trajectory points count:', trajectory.points ? trajectory.points.length : 'NO POINTS');

            // F1 describes tongue height (high F1 = low tongue)
            const startHeightDesc = formants.start_f1 > 500 ? 'Low (저모음)' : formants.start_f1 > 350 ? 'Mid (중모음)' : 'High (고모음)';
            const endHeightDesc = formants.end_f1 > 500 ? 'Low (저모음)' : formants.end_f1 > 350 ? 'Mid (중모음)' : 'High (고모음)';
            setCard('tongue-height', 'Tongue Height (혀 높이)',
                `Start: ${formatNumber(formants.start_f1, 0) || '?'} Hz (${startHeightDesc}) → End: ${formatNumber(formants.end_f1, 0) || '?'} Hz (${endHeightDesc})`);

            // F2 describes tongue position (high F2 = front)
            const startPosDesc = formants.start_f2 > 1800 ? 'Front (전설)' : formants.start_f2 > 1200 ? 'Central (중설)' : 'Back (후설)';
            const endPosDesc = formants.end_f2 > 1800 ? 'Front (전설)' : formants.end_f2 > 1200 ? 'Central (중설)' : 'Back (후설)';
            setCard('tongue-backness', 'Tongue Position (혀 위치)',
                `Start: ${formatNumber(formants.start_f2, 0) || '?'} Hz (${startPosDesc}) → End: ${formatNumber(formants.end_f2, 0) || '?'} Hz (${endPosDesc})`);

            const dirScore = formatNumber(scores.direction, 1);
            const dirQuality = dirScore >= 80 ? 'Excellent (우수)' : dirScore >= 60 ? 'Good (양호)' : 'Needs practice (연습 필요)';
            setCard('lips-roundness', 'Direction Score (방향 점수)', `${dirScore || '?'} / 100 - ${dirQuality}`);
            setCard('breathiness', 'Trajectory Info (궤적 정보)', `${trajectory.num_frames || '?'} frames, ${formatNumber(trajectory.duration, 2) || '?'}s duration (지속시간)`);

            const genderLabel = gender === 'Male' ? 'Male (남성)' : gender === 'Female' ? 'Female (여성)' : gender;
            setCard('tension', 'Voice Analysis (음성 분석)', genderLabel ? `Estimated gender: ${genderLabel}` : 'No gender estimation available (성별 추정 정보 없음)');

            // Show plot container and update dual renderer
            if (plotContainer) {
                const captionText = details.vowel_key
                    ? `${details.vowel_key} Diphthong trajectory (이중모음 궤적)`
                    : 'Diphthong trajectory (이중모음 궤적)';
                if (plotCaption) plotCaption.textContent = captionText;
                plotContainer.hidden = false;

                // Update DualPlotRenderer with trajectory
                if (dualPlotRenderer && trajectory.points && trajectory.points.length > 1) {
                    // Set diphthong start/end references if available
                    if (details.start_ref && details.end_ref) {
                        dualPlotRenderer.setDiphthongReferences(details.start_ref, details.end_ref);
                    }

                    dualPlotRenderer.setPoint({
                        f1: formants.end_f1 || trajectory.points[trajectory.points.length - 1].f1,
                        f2: formants.end_f2 || trajectory.points[trajectory.points.length - 1].f2,
                        trajectory: trajectory.points
                    });
                    console.log('[sound.js] DualPlotRenderer updated with diphthong trajectory:', trajectory.points.length, 'points');
                }
            }
        } else {
            // Monophthong analysis
            // F1: Tongue height description
            const f1Val = formants.f1;
            const f1Ref = reference.f1;
            let f1Hint = '';
            if (f1Val && f1Ref) {
                const f1Diff = f1Val - f1Ref;
                if (Math.abs(f1Diff) <= (reference.f1_sd || 80)) {
                    f1Hint = ' - Good (양호)';
                } else if (f1Diff > 0) {
                    f1Hint = ' - Tongue too low, raise it (혀가 너무 낮음, 올리세요)';
                } else {
                    f1Hint = ' - Tongue too high, lower it (혀가 너무 높음, 내리세요)';
                }
            }
            setCard('tongue-height', 'Tongue Height (혀 높이)', describeMetric(formants.f1, reference.f1, reference.f1_sd, { unit: 'Hz' }) + f1Hint);

            // F2: Tongue position description
            const f2Val = formants.f2;
            const f2Ref = reference.f2;
            let f2Hint = '';
            if (f2Val && f2Ref) {
                const f2Diff = f2Val - f2Ref;
                if (Math.abs(f2Diff) <= (reference.f2_sd || 120)) {
                    f2Hint = ' - Good (양호)';
                } else if (f2Diff > 0) {
                    f2Hint = ' - Tongue too front, move back (혀가 너무 앞쪽, 뒤로 이동)';
                } else {
                    f2Hint = ' - Tongue too back, move forward (혀가 너무 뒤쪽, 앞으로 이동)';
                }
            }
            setCard('tongue-backness', 'Tongue Position (혀 위치)', describeMetric(formants.f2, reference.f2, reference.f2_sd, { unit: 'Hz' }) + f2Hint);

            setCard('lips-roundness', 'Lips Roundness (입술 모양)', describeMetric(formants.f3, reference.f3, null, { unit: 'Hz' }));
            setCard('breathiness', 'Recording Quality (녹음 품질)', qualityHint || 'Good recording quality (녹음 품질 양호)');

            const genderLabel = gender === 'Male' ? 'Male (남성)' : gender === 'Female' ? 'Female (여성)' : gender;
            setCard('tension', 'Voice Analysis (음성 분석)', genderLabel ? `Estimated gender: ${genderLabel}` : 'No gender estimation available (성별 추정 정보 없음)');

            // Show plot container and update dual renderer
            if (plotContainer) {
                const captionText = details.vowel_key
                    ? `${details.vowel_key} Formant position (포만트 위치)`
                    : 'Formant position (포만트 위치)';
                if (plotCaption) plotCaption.textContent = captionText;
                plotContainer.hidden = false;

                // Update DualPlotRenderer with monophthong data
                if (dualPlotRenderer && formants.f1 && formants.f2) {
                    dualPlotRenderer.setPoint({
                        f1: formants.f1,
                        f2: formants.f2,
                        targetF1: reference.f1,
                        targetF2: reference.f2,
                        targetF1_sd: reference.f1_sd,
                        targetF2_sd: reference.f2_sd
                    });
                    console.log('[sound.js] DualPlotRenderer updated with monophthong data');
                }
            }
        }
    };

    const featureOrderForConsonant = ['VOT_ms', 'asp_ratio', 'fric_dur_ms', 'centroid_kHz', 'seg_dur_ms', 'nasal_lowFreq_amp'];

    const renderConsonantCards = (data) => {
        const details = data.details || {};
        const features = details.features || {};
        const adviceList = details.advice_list || [];
        const coaching = details.coaching || '';
        resetPlot();

        featureOrderForConsonant.forEach((featureName, idx) => {
            const stats = features[featureName];
            if (!stats) return;
            if (idx >= metricCardOrder.length) return;
            const cardKey = metricCardOrder[idx];
            const title = consonantFeatureLabels[featureName] || featureName;
            const measuredValue = typeof stats.your_value === 'number'
                ? stats.your_value
                : (details.measured && typeof details.measured[featureName] === 'number'
                    ? details.measured[featureName]
                    : null);
            let decimals = 0;
            let unit = '';
            if (featureName.includes('_ms')) unit = 'ms';
            if (featureName.includes('ratio')) {
                decimals = 3;
            }
            if (featureName.includes('kHz')) {
                unit = 'kHz';
                decimals = 2;
            }
            const body = describeMetric(measuredValue, stats.target_mean, stats.target_sd, { unit, decimals });
            setCard(cardKey, title, body);
        });

        const combinedAdvice = adviceList.length ? adviceList.join(' ') : coaching;
        if (combinedAdvice) {
            setCard('tension', '코칭 (Coaching)', combinedAdvice);
        }
    };

    const renderCardsForAnalysis = (data) => {
        resetCards();
        const type = data.analysis_type;
        if (type === 'vowel') {
            renderVowelCards(data);
            setCard('total', null, '모음 분석 (Vowel analysis)');
        } else if (type === 'consonant') {
            renderConsonantCards(data);
            setCard('total', null, '자음 분석 (Consonant analysis)');
        }
    };

    const setScore = (score) => {
        if (!percentEl) return;
        percentEl.textContent = typeof score === 'number' ? `${score}%` : '';

        const totalCard = cardMap.get('total')?.card;
        if (totalCard && typeof score === 'number') {
            let level = 'poor';
            if (score >= 90) level = 'excellent';
            else if (score >= 75) level = 'good';
            else if (score >= 60) level = 'fair';
            totalCard.setAttribute('data-score-level', level);

            if (feedbackEl) {
                feedbackEl.setAttribute('data-score-level', level);
            }

            const progressFill = document.getElementById('scoreProgressFill');
            if (progressFill) {
                progressFill.style.width = `${score}%`;
            }
        } else {
            const progressFill = document.getElementById('scoreProgressFill');
            if (progressFill) {
                progressFill.style.width = '0%';
            }
        }
    };

    const setStatus = (text) => {
        if (statusEl) statusEl.textContent = text || '';
    };

    const setFeedback = (input) => {
        if (!feedbackEl) return;
        feedbackEl.innerHTML = '';
        if (!input || (Array.isArray(input) && input.length === 0)) {
            feedbackEl.hidden = true;
            return;
        }

        const items = Array.isArray(input)
            ? input.filter(Boolean)
            : String(input).split(/\n+/).map(s => s.trim()).filter(Boolean);

        if (items.length === 0) {
            feedbackEl.hidden = true;
            return;
        }

        feedbackEl.hidden = false;
        const list = document.createElement('ul');
        list.className = 'feedback-list';
        items.forEach(text => {
            const li = document.createElement('li');
            li.textContent = text;
            list.appendChild(li);
        });
        feedbackEl.appendChild(list);
    };

    // 초기 UI 상태 (Initial UI state)
    // Check if current sound is a diphthong for initial message
    const initialSound = localStorage.getItem('selectedSound') ||
        (soundSymbolEl && soundSymbolEl.textContent ? soundSymbolEl.textContent.trim() : '');
    const initialDuration = getRecordingDuration(initialSound) / 1000;
    setStatus(`버튼을 눌러 ${initialDuration}초간 녹음하세요. (Press the button to record for ${initialDuration} second${initialDuration > 1 ? 's' : ''}.)`);
    resetCards();
    setScore('');
    setFeedback('');

    let mediaRecorder;
    let chunks = [];

    async function startRecording() {
        chunks = [];
        btn.disabled = true;
        btn.classList.add('recording');
        btn.setAttribute('aria-pressed', 'true');
        setFeedback('');
        setScore('');
        resetCards();

        // Get current sound symbol and determine recording duration
        const currentSound = localStorage.getItem('selectedSound') ||
            (soundSymbolEl && soundSymbolEl.textContent ? soundSymbolEl.textContent.trim() : '');
        const recordingDuration = getRecordingDuration(currentSound);
        const durationSec = recordingDuration / 1000;

        setStatus(`녹음 중... (${durationSec}초) (Recording… ${durationSec} second${durationSec > 1 ? 's' : ''})`);

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) {
                    chunks.push(e.data);
                }
            };
            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunks, { type: 'audio/webm' });
                window.lastRecording = blob;
                btn.disabled = false;
                btn.classList.remove('recording');
                btn.setAttribute('aria-pressed', 'false');
                setStatus('분석 중... (Analyzing...)');

                stream.getTracks().forEach(track => track.stop());

                try {
                    const userid = parseInt(sessionStorage.getItem('userid') || '0', 10);
                    const sound =
                        localStorage.getItem('selectedSound') ||
                        (soundSymbolEl && soundSymbolEl.textContent ? soundSymbolEl.textContent.trim() : '');

                    if (!sound) {
                        setStatus('선택된 발음 기호를 찾을 수 없습니다. (Could not find selected phonetic symbol.)');
                        return;
                    }

                    const formData = new FormData();
                    formData.append('audio', blob, `recording_${sound}.webm`);
                    formData.append('sound', sound);

                    const endpoint = userid ? '/api/analyze-sound' : '/api/analyze-sound-guest';
                    if (userid) {
                        formData.append('userid', userid.toString());
                    }

                    const response = await fetch(endpoint, { method: 'POST', body: formData });
                    if (!response.ok) {
                        let errorMessage = 'analysis request failed';
                        try {
                            const errPayload = await response.json();
                            if (errPayload && errPayload.detail) {
                                errorMessage = errPayload.detail;
                            }
                        } catch (_) {
                            const fallback = await response.text();
                            if (fallback) errorMessage = fallback;
                        }
                        throw new Error(errorMessage);
                    }

                    const data = await response.json();
                    const score = typeof data.score === 'number'
                        ? data.score
                        : typeof data.result === 'number'
                            ? data.result
                            : 0;
                    setScore(score);

                    const feedbackItems = [];
                    if (data.feedback) {
                        feedbackItems.push(data.feedback);
                    }
                    if (data.details && Array.isArray(data.details.advice_list) && data.details.advice_list.length) {
                        feedbackItems.push(...data.details.advice_list);
                    }
                    setFeedback(feedbackItems);
                    renderCardsForAnalysis(data);
                    setStatus('분석이 완료되었습니다. 다시 녹음하려면 버튼을 누르세요. (Analysis complete. Press the button to record again.)');
                } catch (err) {
                    console.error('Failed to send recording for analysis:', err);
                    const errorMessage = err && err.message ? err.message : '분석 요청에 실패했습니다. (Failed to send analysis request.)';
                    setStatus(`분석 실패: ${errorMessage} (Analysis failed: ${errorMessage})`);
                    setFeedback([`분석 실패: ${errorMessage} (Analysis failed: ${errorMessage})`]);
                    setScore('');
                    resetCards();
                }
            };

            // Start recording with 100ms timeslice to ensure data is captured progressively
            mediaRecorder.start(100);
            setTimeout(() => {
                if (mediaRecorder && mediaRecorder.state === 'recording') {
                    mediaRecorder.stop();
                }
            }, recordingDuration);
        } catch (err) {
            console.error('Failed to start recording:', err);
            btn.disabled = false;
            btn.classList.remove('recording');
            btn.setAttribute('aria-pressed', 'false');
            setStatus('마이크 접근에 실패했습니다. 권한을 확인하세요. (Failed to access microphone. Check permissions.)');
            resetCards();
        }
    }

    btn.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            return;
        }
        startRecording();
    });
})();
