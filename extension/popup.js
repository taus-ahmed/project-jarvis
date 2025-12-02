const micBtn = document.getElementById('micBtn');
const statusDiv = document.getElementById('status');
const outputDiv = document.getElementById('output');

// The Browser's Native Speech Recognition
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = 'en-US';
recognition.continuous = false;

micBtn.onclick = () => {
    recognition.start();
    statusDiv.textContent = "Listening...";
    micBtn.disabled = true;
};

recognition.onresult = (event) => {
    const command = event.results[0][0].transcript.toLowerCase();
    statusDiv.textContent = "Processing...";
    outputDiv.textContent = `You said: "${command}"`;

    // LOGIC: Decide where to send the command
    if (command.includes('youtube') || command.includes('google')) {
        // Handle Web Tasks Here
        handleWebCommand(command);
    } else {
        // Handle Windows Tasks (VS Code, Files, etc)
        sendToPython(command);
    }
    
    micBtn.disabled = false;
};

recognition.onerror = (e) => {
    statusDiv.textContent = "Error: " + e.error;
    micBtn.disabled = false;
};

// --- HANDLER 1: WEB COMMANDS ---
function handleWebCommand(command) {
    statusDiv.textContent = "Executing in Browser...";
    if (command.includes('youtube')) {
        chrome.tabs.create({ url: 'https://www.youtube.com' });
    } else if (command.includes('google')) {
        chrome.tabs.create({ url: 'https://www.google.com' });
    }
}

// --- HANDLER 2: WINDOWS COMMANDS (NATIVE MESSAGING) ---
function sendToPython(text) {
    statusDiv.textContent = "Sending to Windows...";
    
    // 'com.jarvis.bridge' is the name we will give our Python script later
    chrome.runtime.sendNativeMessage('com.jarvis.bridge', { text: text }, (response) => {
        if (chrome.runtime.lastError) {
            outputDiv.textContent = "Error: " + chrome.runtime.lastError.message;
        } else {
            outputDiv.textContent = "Jarvis: " + response.message;
        }
    });
}