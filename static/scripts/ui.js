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
            // Calls placeholder endpoint in main.py – replace backend with real DB/SQL
            const out = await postJson('/api/auth/login', { username, password });
            sessionStorage.setItem('username', out.user || username);
            // update topbar button to username
            if (openBtn) openBtn.textContent = out.user || username;
            close();
        } catch (e) {
            alert(e.message || 'Login failed');
        }
    }

    async function handleSignup() {
        const username = (usernameInput && usernameInput.value || '').trim();
        const password = (passwordInput && passwordInput.value || '').trim();
        if (!username || !password) { alert('Enter username and password'); return; }
        try {
            // Calls placeholder endpoint in main.py – replace backend with real DB/SQL
            const out = await postJson('/api/auth/signup', { username, password });
            alert(out.message || 'Account created');
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
})();


