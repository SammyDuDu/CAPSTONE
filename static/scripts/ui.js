(function () {
    const openBtn = document.getElementById('openLogin');
    const closeBtn = document.getElementById('closeLogin');
    const modal = document.getElementById('loginModal');
    const overlay = document.getElementById('overlay');
    const banner = document.getElementById('firstVisitBanner');
    const bannerClose = document.getElementById('closeFirstVisit');
    const navChip = document.querySelector('.nav-chip');
    const submitLogin = document.getElementById('submitLogin');
    const submitSignup = document.getElementById('submitSignup');
    const usernameInput = document.getElementById('loginUsername');
    const passwordInput = document.getElementById('loginPassword');
    const authModalTitle = document.getElementById('authModalTitle');
    const loginForm = document.getElementById('loginForm');
    const accountForm = document.getElementById('accountForm');
    const accountUser = document.getElementById('accountUser');
    const changePasswordBtn = document.getElementById('changePassword');
    const logoutBtn = document.getElementById('logoutBtn');
    const newPasswordInput = document.getElementById('newPassword');
    const recalibrateBtn = document.getElementById('recalibrateBtn');

    function open() {
        if (overlay) overlay.hidden = false;
        if (modal) modal.hidden = false;
        document.body.style.overflow = 'hidden';
    }
    function close() {
        if (overlay) overlay.hidden = true;
        if (modal) modal.hidden = true;
        document.body.style.overflow = '';
    }

    function openWithView() {
        const u = sessionStorage.getItem('username');
        if (u) {
            // Show account settings
            if (authModalTitle) authModalTitle.textContent = 'Account';
            if (loginForm) loginForm.hidden = true;
            if (accountForm) accountForm.hidden = false;
        } else {
            // Show login form
            if (authModalTitle) authModalTitle.textContent = 'Log in';
            if (loginForm) loginForm.hidden = false;
            if (accountForm) accountForm.hidden = true;
        }
        open();
    }

    if (openBtn) openBtn.addEventListener('click', openWithView);
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (overlay) overlay.addEventListener('click', close);

    async function postJson(url, data) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Request failed');
        }
        return res.json();
    }

    async function getJson(url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error('Request failed');
        return res.json();
    }

    // Update UI when logged in
    function updateLoginState(username, showRecalibrate = true) {
        if (openBtn) openBtn.textContent = username;
        
        // Show/hide recalibrate button
        if (recalibrateBtn) {
            if (showRecalibrate && username) {
                recalibrateBtn.hidden = false;
            } else {
                recalibrateBtn.hidden = true;
            }
        }
    }

    async function handleLogin() {
        const username = (usernameInput && usernameInput.value || '').trim();
        const password = (passwordInput && passwordInput.value || '').trim();

        // Clear previous errors
        const loginError = document.getElementById('loginError');
        if (loginError) loginError.hidden = true;

        // Validate inputs
        if (!username || !password) {
            if (loginError) {
                loginError.textContent = 'Please enter both username and password';
                loginError.hidden = false;
            }
            return;
        }

        // Add loading state
        if (submitLogin) {
            submitLogin.disabled = true;
            submitLogin.classList.add('loading');
        }

        try {
            const out = await postJson('/api/auth/login', { username, password });
            sessionStorage.setItem('username', out.user || username);
            sessionStorage.setItem('userid', out.userid || '');

            // Clear inputs
            if (usernameInput) usernameInput.value = '';
            if (passwordInput) passwordInput.value = '';

            // Update UI
            updateLoginState(out.user || username);

            // Show success toast
            if (window.Toast) {
                window.Toast.success('Welcome back, ' + (out.user || username) + '!', 3000);
            }

            close();

            // Check if calibration is needed
            if (out.calibration_complete === false) {
                // Show calibration modal if not complete (initial signup - non-closable)
                const calOverlay = document.getElementById('calibrationOverlay');
                const calModal = document.getElementById('calibrationModal');
                if (calOverlay && calModal) {
                    if (window.resetCalibration) window.resetCalibration();
                    
                    // Mark as initial signup (non-closable)
                    calOverlay.classList.remove('closable');
                    delete calOverlay.dataset.isRecalibration;
                    
                    calOverlay.hidden = false;
                    calModal.hidden = false;
                    document.body.style.overflow = 'hidden';
                }
            }
        } catch (e) {
            // Show error in modal
            if (loginError) {
                loginError.textContent = e.message || 'Login failed';
                loginError.hidden = false;
            }

            // Also show toast
            if (window.Toast) {
                window.Toast.error(e.message || 'Login failed', 4000);
            }
        } finally {
            // Remove loading state
            if (submitLogin) {
                submitLogin.disabled = false;
                submitLogin.classList.remove('loading');
            }
        }
    }

    async function handleSignup() {
        const username = (usernameInput && usernameInput.value || '').trim();
        const password = (passwordInput && passwordInput.value || '').trim();

        // Clear previous errors
        const signupError = document.getElementById('signupError');
        if (signupError) signupError.hidden = true;

        // Validate with FormValidator
        if (window.FormValidator) {
            const usernameValidation = window.FormValidator.validateUsername(username);
            if (!usernameValidation.valid) {
                if (signupError) {
                    signupError.textContent = usernameValidation.message;
                    signupError.hidden = false;
                }
                return;
            }

            const passwordValidation = window.FormValidator.validatePassword(password);
            if (!passwordValidation.valid) {
                if (signupError) {
                    signupError.textContent = passwordValidation.message;
                    signupError.hidden = false;
                }
                return;
            }
        } else {
            // Fallback validation
            if (!username || !password) {
                if (signupError) {
                    signupError.textContent = 'Please enter both username and password';
                    signupError.hidden = false;
                }
                return;
            }
        }

        // Add loading state
        if (submitSignup) {
            submitSignup.disabled = true;
            submitSignup.classList.add('loading');
        }

        try {
            await postJson('/api/auth/signup', { username, password });

            // Clear input fields
            if (usernameInput) usernameInput.value = '';
            if (passwordInput) passwordInput.value = '';

            // Close login modal immediately
            close();

            // Show success toast
            if (window.Toast) {
                window.Toast.success('Account created successfully!', 2000);
            }

            // Wait a moment before auto-login
            setTimeout(async () => {
                try {
                    const loginOut = await postJson('/api/auth/login', { username, password });
                    sessionStorage.setItem('username', loginOut.user || username);
                    sessionStorage.setItem('userid', loginOut.userid || '');
                    updateLoginState(loginOut.user || username);

                    // Show calibration modal (initial signup - non-closable)
                    const calOverlay = document.getElementById('calibrationOverlay');
                    const calModal = document.getElementById('calibrationModal');
                    if (calOverlay && calModal) {
                        if (window.resetCalibration) window.resetCalibration();
                        
                        // Mark as initial signup (non-closable)
                        calOverlay.classList.remove('closable');
                        delete calOverlay.dataset.isRecalibration;
                        
                        calOverlay.hidden = false;
                        calModal.hidden = false;
                        document.body.style.overflow = 'hidden';
                    }
                } catch (e) {
                    console.error('Auto-login failed:', e);
                    if (window.Toast) {
                        window.Toast.error('Please login with your new account', 4000);
                    }
                }
            }, 1000);

        } catch (e) {
            // Show error in modal
            if (signupError) {
                signupError.textContent = e.message || 'Sign up failed';
                signupError.hidden = false;
            }

            // Also show toast
            if (window.Toast) {
                window.Toast.error(e.message || 'Sign up failed', 4000);
            }
        } finally {
            // Remove loading state
            if (submitSignup) {
                submitSignup.disabled = false;
                submitSignup.classList.remove('loading');
            }
        }
    }

    if (submitLogin) submitLogin.addEventListener('click', handleLogin);
    if (submitSignup) submitSignup.addEventListener('click', handleSignup);

    async function handleChangePassword() {
        const username = sessionStorage.getItem('username');
        const newPassword = (newPasswordInput && newPasswordInput.value || '').trim();
        if (!username) { alert('Not signed in'); return; }
        if (!newPassword) { alert('Enter a new password'); return; }
        try {
            const out = await postJson('/api/auth/change-password', { username, new_password: newPassword });
            alert(out.message || 'Password changed');
            newPasswordInput.value = '';
        } catch (e) {
            alert(e.message || 'Change password failed');
        }
    }

    function handleLogout() {
        sessionStorage.removeItem('username');
        sessionStorage.removeItem('userid');
        // Clear cached progress for previous user
        try {
            const keys = Object.keys(sessionStorage);
            keys.forEach(k => { if (k.startsWith('progress:')) sessionStorage.removeItem(k); });
        } catch (e) {}
        // Reset progress UI on main page
        if (window.location.pathname === '/') {
            const buttons = document.querySelectorAll('.button-grid .hangul-btn');
            buttons.forEach(btn => {
                btn.style.removeProperty('--progress');
                btn.classList.remove('complete');
            });
        }
        updateLoginState(null, false);
        close();
    }

    if (changePasswordBtn) changePasswordBtn.addEventListener('click', handleChangePassword);
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

    // Recalibrate button handler
    if (recalibrateBtn) {
        recalibrateBtn.addEventListener('click', function() {
            const userid = parseInt(sessionStorage.getItem('userid') || '0', 10);
            if (!userid) {
                if (window.Toast) {
                    window.Toast.error('Please log in to recalibrate', 3000);
                }
                return;
            }

            // Open calibration modal (make it closable for recalibration)
            const calOverlay = document.getElementById('calibrationOverlay');
            const calModal = document.getElementById('calibrationModal');
            if (calOverlay && calModal) {
                if (window.resetCalibration) window.resetCalibration();
                
                // Mark as closable (for recalibration, not initial signup)
                calOverlay.classList.add('closable');
                calOverlay.dataset.isRecalibration = 'true';
                
                calOverlay.hidden = false;
                calModal.hidden = false;
                document.body.style.overflow = 'hidden';
                
                if (window.Toast) {
                    window.Toast.info('Starting voice recalibration...', 2000);
                }
            }
        });
    }

    // NOTE: The calibration modal close logic has been MOVED inside the initCalibrationRecord
    // IIFE below so it has access to the calBtn and currentStream variables.

    // On load, if session has username, show it on the button and recalibrate button
    (function initTopbarUser() {
        const u = sessionStorage.getItem('username');
        if (u) {
            updateLoginState(u);
        }
    })();

    // Progress coloring on main page with session cache
    (function initProgressOnIndex() {
        if (window.location.pathname !== '/') return;
        const username = sessionStorage.getItem('username');
        if (!username) return;

        const buttons = Array.from(document.querySelectorAll('.button-grid .hangul-btn'));
        if (buttons.length === 0) return;

        function applyProgress(map) {
            buttons.forEach(btn => {
                const symbol = (btn.textContent || '').trim();
                const pct = map && map[symbol];
                if (typeof pct === 'number') {
                    const clamped = Math.max(0, Math.min(100, pct));
                    btn.style.setProperty('--progress', clamped + '%');
                    if (clamped >= 100) {
                        btn.classList.add('complete');
                    } else {
                        btn.classList.remove('complete');
                    }
                } else {
                    btn.style.removeProperty('--progress');
                    btn.classList.remove('complete');
                }
            });
        }

        // 1) Apply cached progress immediately if available
        try {
            const cacheKey = 'progress:' + username;
            const cached = sessionStorage.getItem(cacheKey);
            if (cached) {
                const parsed = JSON.parse(cached);
                if (parsed && parsed.progress) {
                    applyProgress(parsed.progress);
                }
            }
        } catch (e) {}

        // 2) Fetch fresh progress in background and update + cache
        (async function refresh() {
            try {
                const data = await getJson('/api/progress?username=' + encodeURIComponent(username));
                const map = (data && data.progress) || {};
                applyProgress(map);
                try {
                    sessionStorage.setItem('progress:' + username, JSON.stringify({ progress: map, ts: Date.now() }));
                } catch (e) {}
            } catch (e) {
                // silent
            }
        })();
    })();

    // Mark when navigating via the top-left 'Home' chip, so we know user came from a sound page
    if (navChip) {
        navChip.addEventListener('click', function () {
            // If current page is a sound page, set a flag before navigation
            const onSoundPage = window.location.pathname.includes('/sound');
            if (onSoundPage) {
                try { localStorage.setItem('cameFromSound', '1'); } catch (e) {}
            }
        });
    }

    // First-visit banner logic
    try {
        const cameFromSound = localStorage.getItem('cameFromSound') === '1';
        if (cameFromSound) {
            localStorage.removeItem('cameFromSound');
        } else {
            const hasVisited = localStorage.getItem('hasVisited') === '1';
            if (!hasVisited && banner) {
                banner.hidden = false;
            }
        }
    } catch (e) {}

    if (bannerClose && banner) {
        bannerClose.addEventListener('click', function () {
            banner.hidden = true;
            try { localStorage.setItem('hasVisited', '1'); } catch (e) {}
        });
    }

    // Calibration modal record button - 5 sounds × 3 samples each
    (function initCalibrationRecord() {
        const calBtn = document.getElementById('calibrationRecordBtn');
        const calOverlay = document.getElementById('calibrationOverlay');
        const calModal = document.getElementById('calibrationModal');
        const calPrompt = document.getElementById('calibrationPrompt');
        const calTitle = calModal ? calModal.querySelector('.modal-title') : null;
        const calClose = document.getElementById('closeCalibration'); // Get the 'x' button here
        if (!calBtn) return;

        // 2 calibration sounds with 3 samples each
        // Uses extreme vowels for robust vocal tract scaling:
        // - ㅣ (i): Front-high vowel (highest F2)
        // - ㅜ (u): Back-high vowel (lowest F2)
        const calibrationSounds = [
            { code: 'i', display: 'ㅣ (이)', phonetic: 'ee', hint: 'Smile, tongue high and forward' },
            { code: 'u', display: 'ㅜ (우)', phonetic: 'oo', hint: 'Round lips, tongue high and back' },
        ];
        const SAMPLES_PER_SOUND = 3;

        let currentSoundIndex = 0;
        let currentSampleNum = 1;

        let mediaRecorder;
        let chunks = [];
        let currentStream = null;

        /**
         * Closes the calibration modal and performs necessary cleanup.
         * Only allows closing if it's a recalibration session (not initial signup).
         */
        function closeCalibrationModal() {
            // Only allow closing if it's a recalibration (not initial signup)
            const isRecalibration = calOverlay && calOverlay.dataset.isRecalibration === 'true';

            if (isRecalibration) {
                if (calOverlay) {
                    calOverlay.hidden = true;
                    calOverlay.classList.remove('closable');
                    delete calOverlay.dataset.isRecalibration;
                }
                if (calModal) calModal.hidden = true;
                document.body.style.overflow = '';

                // Stop any active stream and reset button state
                calBtn.disabled = false;
                calBtn.classList.remove('recording');
                calBtn.setAttribute('aria-pressed', 'false');
                if (currentStream) {
                    currentStream.getTracks().forEach(t => t.stop());
                    currentStream = null;
                }

                if (window.Toast) {
                    window.Toast.info('Calibration cancelled', 2000);
                }
            } else {
                // Initial signup - show warning that calibration is required
                if (window.Toast) {
                    window.Toast.warning('Please complete calibration to continue', 3000);
                }
            }
        }

        function updatePrompt() {
            const sound = calibrationSounds[currentSoundIndex];
            const totalSounds = calibrationSounds.length;
            const progress = `(${currentSoundIndex + 1}/${totalSounds}) Sample ${currentSampleNum}/3`;

            if (calPrompt) {
                calPrompt.innerHTML = `Say "<strong>${sound.display}</strong>"<br><span style="font-size: 0.9em; color: var(--color-text-muted);">${progress}</span>`;
            }
            if (calTitle) {
                calTitle.textContent = `Voice Calibration - ${sound.phonetic}`;
            }
        }

        // Expose reset function globally
        window.resetCalibration = function() {
            currentSoundIndex = 0;
            currentSampleNum = 1;
            updatePrompt();
        };

        async function uploadCalibrationRecording(blob, soundCode, sampleNum) {
            try {
                const userid = parseInt(sessionStorage.getItem('userid') || '0');
                if (!userid) {
                    console.error('No userid found');
                    return null;
                }

                const formData = new FormData();
                formData.append('audio', blob, `calibration_${soundCode}_${sampleNum}.webm`);
                formData.append('sound', soundCode);
                formData.append('userid', userid.toString());
                formData.append('sample_num', sampleNum.toString());

                const response = await fetch('/api/calibration', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('Upload failed');
                }

                return await response.json();
            } catch (err) {
                console.error('Failed to upload calibration recording:', err);
                return null;
            }
        }

        async function startCalibrationRecording() {
            if (currentSoundIndex >= calibrationSounds.length) return;

            chunks = [];
            calBtn.disabled = true;
            calBtn.classList.add('recording');
            calBtn.setAttribute('aria-pressed', 'true');

            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                currentStream = stream;
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

                mediaRecorder.onstop = async () => {
                    const blob = new Blob(chunks, { type: 'audio/webm' });
                    const sound = calibrationSounds[currentSoundIndex];

                    // Upload with sample number
                    const result = await uploadCalibrationRecording(blob, sound.code, currentSampleNum);

                    calBtn.disabled = false;
                    calBtn.classList.remove('recording');
                    calBtn.setAttribute('aria-pressed', 'false');
                    stream.getTracks().forEach(t => t.stop());

                    // Show feedback if upload failed
                    if (!result || !result.ok) {
                        if (window.Toast) {
                            window.Toast.error('Recording failed. Please try again.', 3000);
                        }
                        return; // Don't advance, let user retry
                    }

                    // Show success feedback
                    if (window.Toast && result.measured) {
                        window.Toast.success(`F1: ${result.measured.f1}Hz, F2: ${result.measured.f2}Hz`, 2000);
                    }

                    // Advance to next sample or sound
                    if (currentSampleNum < SAMPLES_PER_SOUND) {
                        currentSampleNum++;
                        updatePrompt();
                    } else {
                        // Move to next sound
                        currentSampleNum = 1;
                        currentSoundIndex++;

                        if (currentSoundIndex < calibrationSounds.length) {
                            updatePrompt();
                        } else {
                            // All calibration complete!
                            if (calOverlay) calOverlay.hidden = true;
                            if (calModal) calModal.hidden = true;
                            document.body.style.overflow = '';

                            if (window.Toast) {
                                window.Toast.success('Calibration complete! Your voice profile is ready.', 4000);
                            }

                            // Reset for next time
                            currentSoundIndex = 0;
                            currentSampleNum = 1;
                            updatePrompt();
                        }
                    }
                };

                mediaRecorder.start();
                setTimeout(() => mediaRecorder.stop(), 2500); // 2.5 seconds per sample
            } catch (err) {
                console.error('Recording error:', err);
                calBtn.disabled = false;
                calBtn.classList.remove('recording');
                calBtn.setAttribute('aria-pressed', 'false');
                if (currentStream) {
                    currentStream.getTracks().forEach(t => t.stop());
                    currentStream = null;
                }
                if (window.Toast) {
                    window.Toast.error('Microphone access denied. Please allow microphone access.', 4000);
                }
            }
        }

        calBtn.addEventListener('click', startCalibrationRecording);

        // --- FIXED: Add event listener for the 'x' button to close the modal and stop the stream ---
        if (calClose) {
            calClose.addEventListener('click', closeCalibrationModal);
        }

        // --- FIXED: Add event listener for the overlay to close the modal during recalibration ---
        if (calOverlay) {
            calOverlay.addEventListener('click', function(e) {
                // Only act if the click was directly on the overlay backdrop
                if (e.target === calOverlay) {
                    closeCalibrationModal();
                }
                // Don't propagate to prevent closing during initial signup
                e.stopPropagation();
            });
        }
        // ------------------------------------------------------------------------------------------

        // Initialize prompt
        updatePrompt();
    })();
})();