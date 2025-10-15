const recordButton = document.getElementById('recordButton');
const recordText = document.getElementById('recordText');
const micIcon = document.getElementById('micIcon');
const statusMessage = document.getElementById('statusMessage');
const targetVowelSelect = document.getElementById('targetVowel');
const resultCard = document.getElementById('resultCard');
const scoreDisplay = document.getElementById('scoreDisplay');
const feedbackMessage = document.getElementById('feedbackMessage');
const errorLog = document.getElementById('errorLog');
const errorText = document.getElementById('errorText');

let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// CRITICAL: Use a relative path for the API call in the unified deployment
const mockServerUrl = './api/analyze-vowel'; 

function logError(message) {
    errorLog.classList.remove('hidden');
    errorText.textContent = message;
    console.error(message);
}

function clearFeedback() {
    resultCard.classList.add('hidden');
    errorLog.classList.add('hidden');
    statusMessage.textContent = 'Click to start recording (3 seconds)';
    scoreDisplay.textContent = '--';
    feedbackMessage.textContent = '';
}

async function startRecording() {
    clearFeedback();
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            isRecording = false;
            recordButton.classList.remove('recording', 'bg-red-600');
            recordButton.classList.add('bg-gray-400');
            recordText.textContent = 'Analyzing...';
            micIcon.classList.add('hidden');
            
            // Stop stream tracks to turn off the mic light
            stream.getTracks().forEach(track => track.stop());

            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            sendAudioToServer(audioBlob);
        };

        mediaRecorder.start();
        isRecording = true;
        
        recordButton.classList.remove('bg-red-500');
        recordButton.classList.add('recording', 'bg-red-600');
        recordText.textContent = 'Recording (3s)';
        statusMessage.textContent = 'Recording in progress...';
        
        // Auto-stop after 3 seconds
        setTimeout(() => {
            if (isRecording) {
                mediaRecorder.stop();
            }
        }, 3000);

    } catch (err) {
        logError(`Microphone access denied or failed: ${err.message}`);
    }
}

async function sendAudioToServer(audioBlob) {
    statusMessage.textContent = 'Sending to server for analysis...';
    
    const formData = new FormData();
    const targetVowel = targetVowelSelect.value;
    
    // Append the audio file and the target vowel
    formData.append('audio', audioBlob, 'vowel_recording.webm');
    formData.append('target', targetVowel);

    try {
        const response = await fetch(mockServerUrl, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        // Update UI with results
        scoreDisplay.textContent = result.score;
        feedbackMessage.textContent = result.feedback;
        resultCard.classList.remove('hidden');
        statusMessage.textContent = 'Analysis complete. Click to record again.';

    } catch (err) {
        logError(`Server communication failed. Check the server logs (Render dashboard). Error: ${err.message}`);
        statusMessage.textContent = 'Analysis failed. See error log.';
    } finally {
        recordButton.classList.remove('bg-gray-400');
        recordButton.classList.add('bg-red-500');
        recordText.textContent = 'Record';
        micIcon.classList.remove('hidden');
    }
}

recordButton.addEventListener('click', () => {
    if (!isRecording) {
        startRecording();
    } else {
        // Manually stop recording if button clicked again
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
    }
});

// Initialize state
clearFeedback();