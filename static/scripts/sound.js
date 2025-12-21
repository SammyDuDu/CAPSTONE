// 음성 녹음 후 FastAPI 분석 엔진과 통신
// Record audio and send to FastAPI analysis engine
(function () {
    const RECORDING_DURATION_MS = 1000;  // 1 second for monophthongs
    const DIPHTHONG_DURATION_MS = 1500;  // 1.5 seconds for diphthongs

    // True diphthongs that need trajectory analysis (w-glide vowels)
    // Y-vowels (ㅑ,ㅕ,ㅛ,ㅠ,ㅒ,ㅖ) are treated as monophthongs (short glide + vowel)
    const DIPHTHONG_SYMBOLS = ['ㅘ', 'ㅙ', 'ㅚ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅢ'];

    // Consonant symbols (자음)
    const CONSONANT_SYMBOLS = ['ㄱ', 'ㄲ', 'ㅋ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㅌ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅍ', 'ㅅ', 'ㅆ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅎ'];

    function isConsonant(symbol) {
        return CONSONANT_SYMBOLS.includes(symbol);
    }

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

    // Consonant plot elements
    const consonantPlotContainer = document.getElementById('consonantPlot');
    const consonantPlotCaption = document.getElementById('consonantPlotCaption');

    // Initialize DualPlotRenderer for side-by-side display (vowels)
    let dualPlotRenderer = null;
    const formantCanvas = document.getElementById('formantCanvas');
    const articulatoryCanvas = document.getElementById('articulatoryCanvas');

    /*
    function ensureCanvasSize(canvas) {
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.floor(rect.width * dpr);
        canvas.height = Math.floor(rect.height * dpr);
        const ctx = canvas.getContext('2d');
        if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    */

    function ensureCanvasSize(canvas) {
        const dpr = window.devicePixelRatio || 1;

        // CSS로 고정된 "표시 크기"(CSS px)
        const cssW = canvas.clientWidth;
        const cssH = canvas.clientHeight;
        if (!cssW || !cssH) return;

        const newW = Math.round(cssW * dpr);
        const newH = Math.round(cssH * dpr);

        // 이미 같으면 다시 세팅하지 않음 (불필요 리사이즈/리렌더 방지)
        if (canvas.width === newW && canvas.height === newH) return;

        canvas.width = newW;
        canvas.height = newH;

        const ctx = canvas.getContext('2d');
        if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }


    // --- STOP plot redraw on resize ---
    let stopPlotRAF = null;

    function scheduleRedrawStopPlots() {
    if (stopPlotRAF) return;
    stopPlotRAF = requestAnimationFrame(() => {
        stopPlotRAF = null;
        redrawStopPlots();
    });
}

    let lastStopPlots = null;
    let stopPlotRO = null;

    function redrawStopPlots() {
    if (!lastStopPlots) return;
    if (!plotContainer || plotContainer.hidden) return;

    if (articulatoryCanvas) {
        ensureCanvasSize(articulatoryCanvas);
        drawF2Bar(articulatoryCanvas, lastStopPlots);
    }
    if (formantCanvas) {
        ensureCanvasSize(formantCanvas);
        drawVotF0Scatter(formantCanvas, lastStopPlots);
    }
    }

    /*
    if (formantCanvas) ensureCanvasSize(formantCanvas);
    if (articulatoryCanvas) ensureCanvasSize(articulatoryCanvas);
    window.addEventListener('resize', () => {
    if (formantCanvas) ensureCanvasSize(formantCanvas);
    if (articulatoryCanvas) ensureCanvasSize(articulatoryCanvas);
    });
    */

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

    // Initialize ConsonantPlotRenderer for stop consonants (ㄱ/ㄲ/ㅋ, ㄷ/ㄸ/ㅌ, ㅂ/ㅃ/ㅍ)
    let consonantPlotRenderer = null;
    const placeCanvas = document.getElementById('placeCanvas');
    const votCanvas = document.getElementById('votCanvas');

    if (placeCanvas && votCanvas && typeof ConsonantPlotRenderer !== 'undefined') {
        consonantPlotRenderer = new ConsonantPlotRenderer('placeCanvas', 'votCanvas');
        console.log('[sound.js] ConsonantPlotRenderer initialized');
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
        // Hide vowel plots
        if (plotContainer) plotContainer.hidden = true;
        if (plotCaption) plotCaption.textContent = '';
        if (dualPlotRenderer) {
            dualPlotRenderer.clearTrajectories();
        }
        // Hide consonant plots
        if (consonantPlotContainer) consonantPlotContainer.hidden = true;
        if (consonantPlotCaption) consonantPlotCaption.textContent = '';
        if (consonantPlotRenderer) {
            consonantPlotRenderer.clear();
        }
    };

    const resetCards = () => {
        document.body.classList.remove('stop-mode');
        cardMap.forEach((entry) => {
            if (entry.card) {
            entry.card.hidden = false;   // stop에서 hidden 처리했으면 복구
            entry.card.style.display = ''; // stop에서 display:none 처리했으면 복구
            }

            const defaults = defaultCardState[entry.card?.dataset?.feature] || {};
            // ↑ 이 줄은 없어도 되지만, 아래처럼 key를 그대로 쓰는 방식이면 더 간단해

            // (지금 네 코드처럼 key를 쓰는 게 더 안정적이야)
        });

        // 아래는 너 원래 로직대로 유지하면 됨
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
        if (measured === null) return 'Measurement unavailable';

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

        text += ` (Target ${targetVal}${unitStr}`;
        if (typeof sd === 'number' && !Number.isNaN(sd)) {
            const sdVal = formatNumber(sd, decimals);
            if (sdVal !== null) {
                text += ` ±${sdVal}${unitStr}`;
            }
        }
        text += `, Diff ${diffStr}${unitStr})`;
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
            const startHeightDesc = formants.start_f1 > 500 ? 'Low' : formants.start_f1 > 350 ? 'Mid' : 'High';
            const endHeightDesc = formants.end_f1 > 500 ? 'Low' : formants.end_f1 > 350 ? 'Mid' : 'High';
            setCard('tongue-height', 'Tongue Height',
                `Start: ${formatNumber(formants.start_f1, 0) || '?'} Hz (${startHeightDesc}) → End: ${formatNumber(formants.end_f1, 0) || '?'} Hz (${endHeightDesc})`);

            // F2 describes tongue position (high F2 = front)
            const startPosDesc = formants.start_f2 > 1800 ? 'Front' : formants.start_f2 > 1200 ? 'Central' : 'Back';
            const endPosDesc = formants.end_f2 > 1800 ? 'Front' : formants.end_f2 > 1200 ? 'Central' : 'Back';
            setCard('tongue-backness', 'Tongue Position',
                `Start: ${formatNumber(formants.start_f2, 0) || '?'} Hz (${startPosDesc}) → End: ${formatNumber(formants.end_f2, 0) || '?'} Hz (${endPosDesc})`);

            const dirScore = formatNumber(scores.direction, 1);
            const dirQuality = dirScore >= 80 ? 'Excellent' : dirScore >= 60 ? 'Good' : 'Needs practice';
            setCard('lips-roundness', 'Direction Score', `${dirScore || '?'} / 100 - ${dirQuality}`);
            setCard('breathiness', 'Trajectory Info', `${trajectory.num_frames || '?'} frames, ${formatNumber(trajectory.duration, 2) || '?'}s duration`);

            const genderLabel = gender === 'Male' ? 'Male' : gender === 'Female' ? 'Female' : gender;
            setCard('tension', 'Voice Analysis', genderLabel ? `Estimated gender: ${genderLabel}` : 'No gender estimation available');

            // Show plot container and update dual renderer
            if (plotContainer) {
                const captionText = details.vowel_key
                    ? `${details.vowel_key} Diphthong trajectory`
                    : 'Diphthong trajectory';
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
                    f1Hint = ' - Good';
                } else if (f1Diff > 0) {
                    f1Hint = ' - Tongue too low, raise it';
                } else {
                    f1Hint = ' - Tongue too high, lower it';
                }
            }
            setCard('tongue-height', 'Tongue Height', describeMetric(formants.f1, reference.f1, reference.f1_sd, { unit: 'Hz' }) + f1Hint);

            // F2: Tongue position description
            const f2Val = formants.f2;
            const f2Ref = reference.f2;
            let f2Hint = '';
            if (f2Val && f2Ref) {
                const f2Diff = f2Val - f2Ref;
                if (Math.abs(f2Diff) <= (reference.f2_sd || 120)) {
                    f2Hint = ' - Good';
                } else if (f2Diff > 0) {
                    f2Hint = ' - Tongue too front, move back';
                } else {
                    f2Hint = ' - Tongue too back, move forward';
                }
            }
            setCard('tongue-backness', 'Tongue Position', describeMetric(formants.f2, reference.f2, reference.f2_sd, { unit: 'Hz' }) + f2Hint);

            setCard('lips-roundness', 'Lips Roundness', describeMetric(formants.f3, reference.f3, null, { unit: 'Hz' }));
            setCard('breathiness', 'Recording Quality', qualityHint || 'Good recording quality');

            const genderLabel = gender === 'Male' ? 'Male' : gender === 'Female' ? 'Female' : gender;
            setCard('tension', 'Voice Analysis', genderLabel ? `Estimated gender: ${genderLabel}` : 'No gender estimation available');

            // Show plot container and update dual renderer
            if (plotContainer) {
                const captionText = details.vowel_key
                    ? `${details.vowel_key} Formant position`
                    : 'Formant position';
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
        const consonantType = details.type || data.consonant_type || 'unknown';
        const feedbackText = data.feedback || '';

        // Debug logging
        console.log('[sound.js] renderConsonantCards called');
        console.log('[sound.js] consonantType:', consonantType);
        console.log('[sound.js] details:', JSON.stringify(details, null, 2));

        // Reset all plots first
        resetPlot();

        // Hide only the 5 feature cards for consonants (keep Total card visible)
        const featureCards = document.querySelectorAll('.card:not(.total)');
        featureCards.forEach(card => {
            card.style.display = 'none';
        });

        // Add consonant-mode class for compact layout
        const cardsSection = document.querySelector('.cards');
        if (cardsSection) {
            cardsSection.classList.add('consonant-mode');
        }

        // Get single plot elements
        const singlePlotContainer = document.getElementById('singleConsonantPlot');
        const singlePlotCaption = document.getElementById('singleConsonantPlotCaption');
        const spectralCanvas = document.getElementById('spectralCanvas');

        const syllable = details.syllable || localStorage.getItem('selectedSound') || '';

        // Handle different consonant types
        if (consonantType === 'stop') {
            // Stop consonants: 2 plots (place + VOT-F0z)
            const evaluation = details.evaluation || {};
            const targets = details.targets || {};

            if (evaluation && consonantPlotRenderer && consonantPlotContainer) {
                const stopData = {
                    type: 'stop',
                    targets: targets,
                    evaluation: evaluation
                };
                consonantPlotRenderer.update(stopData);
                consonantPlotContainer.hidden = false;

                if (consonantPlotCaption) {
                    consonantPlotCaption.textContent = `${syllable} 파열음 분석`;
                }
                console.log('[sound.js] Stop consonant: 2 plots shown');
            }
        } else if (consonantType === 'fricative' || consonantType === 'affricate') {
            // Fricative/Affricate: 1 plot (spectral)
            if (singlePlotContainer) {
                singlePlotContainer.hidden = false;
                // Draw simple spectral visualization
                if (spectralCanvas) {
                    drawSimpleSpectralPlot(spectralCanvas, details, consonantType);
                }
                if (singlePlotCaption) {
                    const typeLabel = consonantType === 'fricative' ? '마찰음' : '파찰음';
                    singlePlotCaption.textContent = `${syllable} ${typeLabel} 분석`;
                }
                console.log('[sound.js] Fricative/Affricate: 1 plot shown');
            }
        } else if (consonantType === 'nasal' || consonantType === 'liquid') {
            // Nasal/Liquid: no plot
            console.log('[sound.js] Nasal/Liquid: no plot');
        }

        // Return feedback text for main feedback area
        return feedbackText;
    };

    // Simple spectral plot for fricatives/affricates
    const drawSimpleSpectralPlot = (canvas, details, type) => {
        const ctx = canvas.getContext('2d');
        const w = canvas.width = 600;
        const h = canvas.height = 200;

        // Clear
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, w, h);

        const evaluation = details.evaluation || {};
        const targets = details.targets || {};

        // Get detected and target
        const detected = evaluation.detected_fricative || evaluation.detected_affricate;
        const target = targets.fricative || targets.affricate;

        // Labels and positions based on type
        let labels, positions, labelSymbols;
        if (type === 'fricative') {
            // ㅆ (ss/fortis) - ㅅ (s/lenis) - ㅎ (h/aspirated)
            labels = ['ss', 's', 'h'];
            labelSymbols = ['ㅆ', 'ㅅ', 'ㅎ'];
        } else {
            // Affricate: ㅉ (fortis) - ㅈ (lenis) - ㅊ (aspirated)
            labels = ['fortis', 'lenis', 'aspirated'];
            labelSymbols = ['ㅉ', 'ㅈ', 'ㅊ'];
        }
        positions = { [labels[0]]: 0, [labels[1]]: 0.5, [labels[2]]: 1 };

        // Draw title
        ctx.fillStyle = '#374151';
        ctx.font = '14px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        const targetSymbol = labelSymbols[labels.indexOf(target)] || target;
        const detectedSymbol = labelSymbols[labels.indexOf(detected)] || detected;
        ctx.fillText(`Which ${type} does it sound closer to?`, w / 2, 30);
        ctx.fillText(`(target: ${targetSymbol}, detected: ${detectedSymbol})`, w / 2, 50);

        // Slider line
        const sliderY = 120;
        const sliderStartX = 80;
        const sliderEndX = w - 80;
        const sliderWidth = sliderEndX - sliderStartX;

        // Draw slider track
        ctx.strokeStyle = '#94a3b8';
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(sliderStartX, sliderY);
        ctx.lineTo(sliderEndX, sliderY);
        ctx.stroke();

        // Draw position markers for each sound
        labels.forEach((label, idx) => {
            const x = sliderStartX + positions[label] * sliderWidth;

            // Small circle marker
            ctx.beginPath();
            ctx.arc(x, sliderY, 8, 0, Math.PI * 2);
            ctx.fillStyle = label === target ? '#3b82f6' : '#94a3b8';
            ctx.fill();

            // Label below
            ctx.fillStyle = '#374151';
            ctx.font = 'bold 18px Inter, system-ui, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(labelSymbols[idx], x, sliderY + 35);
        });

        // Draw user position (detected)
        if (detected && positions[detected] !== undefined) {
            const userX = sliderStartX + positions[detected] * sliderWidth;

            // User marker (larger orange circle above)
            ctx.beginPath();
            ctx.arc(userX, sliderY - 30, 14, 0, Math.PI * 2);
            ctx.fillStyle = '#f97316';
            ctx.fill();

            // "You" label
            ctx.fillStyle = '#374151';
            ctx.font = '12px Inter, system-ui, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('You', userX, sliderY - 50);
        }

        // Border
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;
        ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
    };

    const renderCardsForAnalysis = (data) => {
        const type = data.analysis_type;
        const featureCards = document.querySelectorAll('.card:not(.total)');

        if (type === 'vowel') {
            // Show all feature cards for vowels
            featureCards.forEach(card => {
                card.style.display = '';
            });
            // Remove consonant-mode class if present
            const cardsSection = document.querySelector('.cards');
            if (cardsSection) {
                cardsSection.classList.remove('consonant-mode');
            }
            resetCards();
            renderVowelCards(data);
            setCard('total', null, 'Vowel analysis');
        } else if (type === 'consonant') {
            // renderConsonantCards hides feature cards and draws plots
            renderConsonantCards(data);
            // Set Total card text for consonant analysis
            setCard('total', null, 'Consonant analysis');
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

        // Flatten: if input is array, split each item by newline; if string, split directly
        let items = [];
        if (Array.isArray(input)) {
            input.filter(Boolean).forEach(item => {
                const parts = String(item).split(/\n+/).map(s => s.trim()).filter(Boolean);
                items.push(...parts);
            });
        } else {
            items = String(input).split(/\n+/).map(s => s.trim()).filter(Boolean);
        }

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
    setStatus(`Press the button to record for ${initialDuration} second${initialDuration > 1 ? 's' : ''}.`);
    resetCards();
    setScore('');
    setFeedback('');

    // Hide feature cards (not Total) for consonants on initial load
    if (isConsonant(initialSound)) {
        const featureCards = document.querySelectorAll('.card:not(.total)');
        featureCards.forEach(card => {
            card.style.display = 'none';
        });
        // Add consonant-mode class for compact layout
        const cardsSection = document.querySelector('.cards');
        if (cardsSection) {
            cardsSection.classList.add('consonant-mode');
        }
    }

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

        setStatus(`Recording... (${durationSec} second${durationSec > 1 ? 's' : ''})`);

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
                setStatus('Analyzing...');

                stream.getTracks().forEach(track => track.stop());

                try {
                    const userid = parseInt(sessionStorage.getItem('userid') || '0', 10);
                    /*
                    const sound =
                        localStorage.getItem('selectedSound') ||
                        (soundSymbolEl && soundSymbolEl.textContent ? soundSymbolEl.textContent.trim() : '');

                    if (!sound) {
                        setStatus('Could not find selected phonetic symbol.');
                        return;
                    }

                    const formData = new FormData();
                    formData.append('audio', blob, `recording_${sound}.webm`);
                    formData.append('sound', sound);
                    */

                    const rawSound =
                    localStorage.getItem('selectedSound') ||
                    (soundSymbolEl && soundSymbolEl.textContent ? soundSymbolEl.textContent.trim() : '');

                    if (!rawSound) {
                    setStatus('Could not find selected phonetic symbol.');
                    return;
                    }

                    const soundForBackend = normalizeSoundForBackend(rawSound);

                    const formData = new FormData();
                    formData.append('audio', blob, `recording_${soundForBackend}.webm`);
                    formData.append('sound', soundForBackend);

                    const endpoint = userid ? '/api/analyze-sound' : '/api/analyze-sound-guest';
                    if (userid) {
                        formData.append('userid', userid.toString());
                    }

                    const response = await fetch(endpoint, { method: 'POST', body: formData });
                    if (!response.ok) {
                    // Read body ONCE
                    const raw = await response.text();

                    // Try to parse JSON error, otherwise keep raw text
                    let errorMessage = 'analysis request failed';
                    try {
                        const errPayload = JSON.parse(raw);
                        if (errPayload && errPayload.detail) {
                        errorMessage = errPayload.detail;
                        } else if (errPayload && errPayload.error) {
                        errorMessage = errPayload.error;
                        } else if (raw) {
                        errorMessage = raw;
                        }
                    } catch (_) {
                        if (raw) errorMessage = raw;
                    }

                    throw new Error(errorMessage);
                    }


                    const data = await response.json();
                    const score = typeof data.score === 'number'
                        ? data.score
                        : typeof data.result === 'number'
                            ? data.result
                            : 0;

                    // Show score for all analysis types
                    setScore(score);

                    const feedbackItems = [];

                    if (data.analysis_type === 'consonant' && data.details?.type === 'stop') {
                        // stop consonants: use backend-generated feedback only
                        if (data.feedback) {
                            feedbackItems.push(data.feedback);
                        }
                    } else {
                        // vowels or non-stop consonants
                        if (data.feedback) {
                            feedbackItems.push(data.feedback);
                        }
                        if (data.details && Array.isArray(data.details.advice_list) && data.details.advice_list.length) {
                            feedbackItems.push(...data.details.advice_list);
                        }
                    }

                    setFeedback(feedbackItems);
                    renderCardsForAnalysis(data);
                    setStatus('Analysis complete. Press the button to record again.');
                } catch (err) {
                    console.error('Failed to send recording for analysis:', err);
                    const errorMessage = err && err.message ? err.message : 'Failed to send analysis request.';
                    setStatus(`Analysis failed: ${errorMessage}`);
                    setFeedback([`Analysis failed: ${errorMessage}`]);
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
            setStatus('Failed to access microphone. Check permissions.');
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

// 🔴 TEMP DEBUG — remove later
window.DEBUG_STOP_PAYLOAD = {
  details: {
    type: "stop",
    evaluation: {
      plots: {
        f2_centers_hz: { labial: 1200, alveolar: 1700, velar: 2200 },
        f2_tolerance_hz: 600,
        f2_user_hz: 1446,
        vot_f0_point: { x_vot_ms: 83.5, y_f0_z: 1.36 },
        vot_reference_ranges_ms: {
          fortis: { low: 0, high: 20, center: 10 },
          lenis: { low: 20, high: 50, center: 35 },
          aspirated: { low: 60, high: 100, center: 80 }
        },
        f0z_reference_targets: {
          lenis: { center: -0.5, tol: 0.7 },
          fortis: { center: 1.0, tol: 0.7 },
          aspirated: { center: 0.6, tol: 0.7 }
        }
      }
    }
  }
};
