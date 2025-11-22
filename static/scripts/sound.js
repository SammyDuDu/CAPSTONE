// 2초 음성 녹음 후 FastAPI 분석 엔진과 통신
(function () {
    const RECORDING_DURATION_MS = 2000;
    const btn = document.getElementById('recordBtn');
    if (!btn) return;

    const percentEl = document.querySelector('.card.total .percent');
    const statusEl = document.getElementById('analysisStatus');
    const feedbackEl = document.getElementById('analysisFeedback');
    const soundSymbolEl = document.getElementById('soundSymbol');
    const cards = Array.from(document.querySelectorAll('.card[data-feature]'));
    const plotContainer = document.getElementById('analysisPlot');
    const plotImage = document.getElementById('analysisPlotImage');
    const plotCaption = document.getElementById('analysisPlotCaption');

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
        if (plotImage) {
            plotImage.removeAttribute('src');
            plotImage.alt = '';
        }
        if (plotCaption) plotCaption.textContent = '';
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
        if (measured === null) return '측정 불가';

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

        text += ` (목표 ${targetVal}${unitStr}`;
        if (typeof sd === 'number' && !Number.isNaN(sd)) {
            const sdVal = formatNumber(sd, decimals);
            if (sdVal !== null) {
                text += ` ±${sdVal}${unitStr}`;
            }
        }
        text += `, 차이 ${diffStr}${unitStr})`;
        return text;
    };

    const renderVowelCards = (data) => {
        const details = data.details || {};
        const formants = details.formants || {};
        const reference = details.reference || {};
        const qualityHint = details.quality_hint;
        const gender = details.gender;

        setCard('tongue-height', 'Tongue Height', describeMetric(formants.f1, reference.f1, reference.f1_sd, { unit: 'Hz' }));
        setCard('tongue-backness', 'Tongue Backness', describeMetric(formants.f2, reference.f2, reference.f2_sd, { unit: 'Hz' }));
        setCard('lips-roundness', 'Lips Roundness', describeMetric(formants.f3, reference.f3, null, { unit: 'Hz' }));
        setCard('breathiness', 'Breathiness', qualityHint || '녹음 품질 양호');
        const genderLabel = gender === 'Male' ? '남성' : gender === 'Female' ? '여성' : gender;
        setCard('tension', 'Tension', genderLabel ? `예상 성별: ${genderLabel}` : '성별 추정 정보 없음');

        if (details.plot_url && plotContainer && plotImage) {
            plotImage.src = details.plot_url;
            const captionText = details.vowel_key ? `${details.vowel_key} 포만트 위치` : '포만트 위치';
            plotImage.alt = captionText;
            if (plotCaption) plotCaption.textContent = captionText;
            plotContainer.hidden = false;
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
            setCard('tension', '코칭', combinedAdvice);
        }
    };

    const renderCardsForAnalysis = (data) => {
        resetCards();
        const type = data.analysis_type;
        if (type === 'vowel') {
            renderVowelCards(data);
            setCard('total', null, '모음 분석');
        } else if (type === 'consonant') {
            renderConsonantCards(data);
            setCard('total', null, '자음 분석');
        }
    };

    const setScore = (score) => {
        if (!percentEl) return;
        percentEl.textContent = typeof score === 'number' ? `${score}%` : '';
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

    // 초기 UI 상태
    resetCards();
    setScore('');
    setFeedback('');
    setStatus('버튼을 눌러 2초간 녹음하세요.');

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
        setStatus('녹음 중... (2초)');

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
                setStatus('분석 중...');

                stream.getTracks().forEach(track => track.stop());

                try {
                    const userid = parseInt(sessionStorage.getItem('userid') || '0', 10);
                    const sound =
                        localStorage.getItem('selectedSound') ||
                        (soundSymbolEl && soundSymbolEl.textContent ? soundSymbolEl.textContent.trim() : '');

                    if (!sound) {
                        setStatus('선택된 발음 기호를 찾을 수 없습니다.');
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
                    setStatus('분석이 완료되었습니다. 다시 녹음하려면 버튼을 누르세요.');
                } catch (err) {
                    console.error('Failed to send recording for analysis:', err);
                    const errorMessage = err && err.message ? err.message : '분석 요청에 실패했습니다.';
                    setStatus(`분석 실패: ${errorMessage}`);
                    setFeedback([`분석 실패: ${errorMessage}`]);
                    setScore('');
                    resetCards();
                }
            };

            mediaRecorder.start();
            setTimeout(() => {
                if (mediaRecorder && mediaRecorder.state === 'recording') {
                    mediaRecorder.stop();
                }
            }, RECORDING_DURATION_MS);
        } catch (err) {
            console.error('Failed to start recording:', err);
            btn.disabled = false;
            btn.classList.remove('recording');
            btn.setAttribute('aria-pressed', 'false');
            setStatus('마이크 접근에 실패했습니다. 권한을 확인하세요.');
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
