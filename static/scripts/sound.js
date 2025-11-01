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
                window.lastRecording = blob;
                btn.disabled = false;
                btn.classList.remove('recording');
                btn.setAttribute('aria-pressed', 'false');
                // stop tracks to release mic
                stream.getTracks().forEach(t => t.stop());

                // Send audio to server for analysis
                try {
                    const userid = parseInt(sessionStorage.getItem('userid') || '0');
                    const sound = localStorage.getItem('selectedSound') || (document.getElementById('soundSymbol')?.textContent || '').trim();
                    
                    if (!sound) {
                        console.warn('Cannot analyze: missing sound');
                        return;
                    }
                    
                    const formData = new FormData();
                    formData.append('audio', blob, `recording_${sound}.webm`);
                    formData.append('sound', sound);
                    
                    // Use guest endpoint if not logged in, otherwise use logged-in endpoint
                    const endpoint = userid ? '/api/analyze-sound' : '/api/analyze-sound-guest';
                    if (userid) {
                        formData.append('userid', userid.toString());
                    }
                    
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        const result = data.result || 0;
                        // Update the UI percent box with analysis result
                        if (percentEl) {
                            percentEl.textContent = result + '%';
                        }
                    } else {
                        console.error('Analysis failed:', await response.text());
                    }
                } catch (err) {
                    console.error('Failed to send recording for analysis:', err);
                }
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


