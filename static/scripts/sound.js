// Simple 3s recorder using MediaRecorder; stores the Blob but does nothing with it yet
(function () {
    const btn = document.getElementById('recordBtn');
    if (!btn) return;
    const percentEl = document.querySelector('.card.total .percent');
    // On page load, hide previous percent and show only 'total'
    if (percentEl) percentEl.textContent = '';

    let mediaRecorder;
    let chunks = [];

    async function startRecording() {
        chunks = [];
        btn.disabled = true;
        btn.classList.add('recording');
        btn.setAttribute('aria-pressed', 'true');
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunks, { type: 'audio/webm' });
                window.lastRecording = blob; // available for later upload
                btn.disabled = false;
                btn.classList.remove('recording');
                btn.setAttribute('aria-pressed', 'false');
                // stop tracks to release mic
                stream.getTracks().forEach(t => t.stop());

                // Generate a random progress value 0..100
                const randomProgress = Math.floor(Math.random() * 101);
                // Update the UI percent box
                if (percentEl) {
                    percentEl.textContent = randomProgress + '%';
                }
                // Send to backend if logged in
                try {
                    const username = sessionStorage.getItem('username');
                    const sound = localStorage.getItem('selectedSound') || (document.getElementById('soundSymbol')?.textContent || '').trim();
                    if (username && sound) {
                        await fetch('/api/update-progress', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ username, sound, progress: randomProgress })
                        });
                    }
                } catch (_) { /* ignore */ }
            };
            mediaRecorder.start();
            setTimeout(() => mediaRecorder.stop(), 3000);
        } catch (err) {
            btn.disabled = false;
            btn.classList.remove('recording');
            btn.setAttribute('aria-pressed', 'false');
        }
    }

    btn.addEventListener('click', startRecording);
})();


