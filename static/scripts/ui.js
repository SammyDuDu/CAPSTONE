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

    async function handleLogin() {
        const username = (usernameInput && usernameInput.value || '').trim();
        const password = (passwordInput && passwordInput.value || '').trim();
        if (!username || !password) { alert('Enter username and password'); return; }
        try {
            const out = await postJson('/api/auth/login', { username, password });
            sessionStorage.setItem('username', out.user || username);
            sessionStorage.setItem('userid', out.userid || '');
            // update topbar button to username
            if (openBtn) openBtn.textContent = out.user || username;
            close();
            
            // Check if calibration is needed
            if (out.calibration_complete === false) {
                // Show calibration modal if not complete
                const calOverlay = document.getElementById('calibrationOverlay');
                const calModal = document.getElementById('calibrationModal');
                if (calOverlay && calModal) {
                    if (window.resetCalibration) window.resetCalibration();
                    calOverlay.hidden = false;
                    calModal.hidden = false;
                    document.body.style.overflow = 'hidden';
                }
            }
        } catch (e) {
            alert(e.message || 'Login failed');
        }
    }

    async function handleSignup() {
        const username = (usernameInput && usernameInput.value || '').trim();
        const password = (passwordInput && passwordInput.value || '').trim();
        if (!username || !password) { alert('Enter username and password'); return; }
        try {
            const out = await postJson('/api/auth/signup', { username, password });
            
            // Clear input fields
            if (usernameInput) usernameInput.value = '';
            if (passwordInput) passwordInput.value = '';
            
            // Close login modal immediately
            close();
            
            // Show "user created" banner (show it briefly, then show calibration)
            const userCreatedBanner = document.getElementById('userCreatedBanner');
            if (userCreatedBanner) {
                userCreatedBanner.hidden = false;
                // Wait a moment before auto-login and calibration modal
                setTimeout(async () => {
                    // Auto-login the newly created user
                    try {
                        const loginOut = await postJson('/api/auth/login', { username, password });
                        sessionStorage.setItem('username', loginOut.user || username);
                        sessionStorage.setItem('userid', loginOut.userid || '');
                        if (openBtn) openBtn.textContent = loginOut.user || username;
                    } catch (e) {
                        console.error('Auto-login failed:', e);
                    }
                    
                    // Hide banner and show calibration modal
                    if (userCreatedBanner) userCreatedBanner.hidden = true;
                    
            // Show non-closable calibration modal
            const calOverlay = document.getElementById('calibrationOverlay');
            const calModal = document.getElementById('calibrationModal');
            if (calOverlay && calModal) {
                // Reset calibration state
                if (window.resetCalibration) window.resetCalibration();
                calOverlay.hidden = false;
                calModal.hidden = false;
                document.body.style.overflow = 'hidden';
            }
                }, 1500); // Show banner for 1.5 seconds
            } else {
                // Fallback if banner doesn't exist - proceed with auto-login and modal
                try {
                    const loginOut = await postJson('/api/auth/login', { username, password });
                    sessionStorage.setItem('username', loginOut.user || username);
                    sessionStorage.setItem('userid', loginOut.userid || '');
                    if (openBtn) openBtn.textContent = loginOut.user || username;
                } catch (e) {
                    console.error('Auto-login failed:', e);
                }
                const calOverlay = document.getElementById('calibrationOverlay');
                const calModal = document.getElementById('calibrationModal');
                if (calOverlay && calModal) {
                    // Reset calibration state
                    if (window.resetCalibration) window.resetCalibration();
                    calOverlay.hidden = false;
                    calModal.hidden = false;
                    document.body.style.overflow = 'hidden';
                }
            }
        } catch (e) {
            alert(e.message || 'Sign up failed');
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
        if (openBtn) openBtn.textContent = 'log in';
        close();
    }

    if (changePasswordBtn) changePasswordBtn.addEventListener('click', handleChangePassword);
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

    // On load, if session has username, show it on the button
    (function initTopbarUser() {
        const u = sessionStorage.getItem('username');
        if (u && openBtn) openBtn.textContent = u;
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

    // Mark when navigating via the top-left '한글' chip, so we know user came from a sound page
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

    // Calibration modal record button - 3 consecutive recordings
    (function initCalibrationRecord() {
        const calBtn = document.getElementById('calibrationRecordBtn');
        const calOverlay = document.getElementById('calibrationOverlay');
        const calModal = document.getElementById('calibrationModal');
        const calPrompt = document.getElementById('calibrationPrompt');
        if (!calBtn) return;

        // Make overlay non-closable
        if (calOverlay) {
            calOverlay.addEventListener('click', function(e) {
                e.stopPropagation(); // prevent closing
            });
        }

        // Sound codes for server: 'a', 'e', 'u'
        // Display texts: "aaa", "eee", "uuu"
        const soundCodes = ['a', 'e', 'u'];
        const soundDisplays = ['aaa', 'eee', 'uuu'];
        let currentIndex = 0;
        
        // Expose reset function globally
        window.resetCalibration = function() {
            currentIndex = 0;
            if (calPrompt) calPrompt.textContent = 'Say "' + soundDisplays[0] + '"';
        };
        let mediaRecorder;
        let chunks = [];
        let currentStream = null;

        async function uploadCalibrationRecording(blob, soundCode) {
            try {
                const userid = parseInt(sessionStorage.getItem('userid') || '0');
                if (!userid) {
                    console.error('No userid found');
                    return;
                }
                
                const formData = new FormData();
                formData.append('audio', blob, `calibration_${soundCode}.webm`);
                formData.append('sound', soundCode);
                formData.append('userid', userid.toString());

                await fetch('/api/calibration', {
                    method: 'POST',
                    body: formData
                });
            } catch (err) {
                console.error('Failed to upload calibration recording:', err);
            }
        }

        async function startCalibrationRecording() {
            if (currentIndex >= soundCodes.length) return;
            
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
                    const soundCode = soundCodes[currentIndex];
                    
                    // Upload to server with sound code ('a', 'e', 'u')
                    await uploadCalibrationRecording(blob, soundCode);
                    
                    calBtn.disabled = false;
                    calBtn.classList.remove('recording');
                    calBtn.setAttribute('aria-pressed', 'false');
                    stream.getTracks().forEach(t => t.stop());
                    
                    currentIndex++;
                    
                    if (currentIndex < soundCodes.length) {
                        // Show next prompt with display text
                        if (calPrompt) {
                            calPrompt.textContent = 'Say "' + soundDisplays[currentIndex] + '"';
                        }
                    } else {
                        // All recordings done - close modal
                        if (calOverlay) calOverlay.hidden = true;
                        if (calModal) calModal.hidden = true;
                        document.body.style.overflow = '';
                        // Reset for next time
                        currentIndex = 0;
                        if (calPrompt) calPrompt.textContent = 'Say "' + soundDisplays[0] + '"';
                    }
                };
                mediaRecorder.start();
                setTimeout(() => mediaRecorder.stop(), 3000);
            } catch (err) {
                calBtn.disabled = false;
                calBtn.classList.remove('recording');
                calBtn.setAttribute('aria-pressed', 'false');
                if (currentStream) {
                    currentStream.getTracks().forEach(t => t.stop());
                    currentStream = null;
                }
            }
        }

        calBtn.addEventListener('click', startCalibrationRecording);
    })();
})();


