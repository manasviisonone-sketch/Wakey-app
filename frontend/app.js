// ==================== CONFIG ====================
const API_URL = 'http://localhost:3001/api';

// ==================== STATE ====================
let currentUser = null;
let friends = [];
let alarms = [];
let currentAlarm = null;
let isDarkMode = false;
let alarmAudio = null; // Audio player for alarm sounds

// ==================== THEME TOGGLE ====================
function toggleTheme() {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('dark-mode');
    
    const themeToggle = document.getElementById('theme-toggle');
    themeToggle.textContent = isDarkMode ? '☀️' : '🌙';
    
    // Save preference
    localStorage.setItem('wakeyTheme', isDarkMode ? 'dark' : 'light');
}

// Load saved theme
function loadTheme() {
    const savedTheme = localStorage.getItem('wakeyTheme');
    if (savedTheme === 'dark') {
        isDarkMode = true;
        document.body.classList.add('dark-mode');
        document.getElementById('theme-toggle').textContent = '☀️';
    }
}

// ==================== UTILITY FUNCTIONS ====================
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

function showModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function showError(elementId, message) {
    document.getElementById(elementId).textContent = message;
    setTimeout(() => {
        document.getElementById(elementId).textContent = '';
    }, 3000);
}

// ==================== API CALLS ====================
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(`${API_URL}${endpoint}`, options);
    return await response.json();
}

// ==================== AUTH ====================
document.addEventListener('DOMContentLoaded', () => {
    // Load theme first
    loadTheme();
    
    // Theme toggle button
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    
    // Check if user is logged in
    const savedUser = localStorage.getItem('wakeyUser');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        loadDashboard();
    }

    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
            
            tab.classList.add('active');
            const formId = tab.dataset.tab + '-form';
            document.getElementById(formId).classList.add('active');
        });
    });

    // Login
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        
        const result = await apiCall('/login', 'POST', { username, password });
        
        if (result.success) {
            currentUser = result.user;
            localStorage.setItem('wakeyUser', JSON.stringify(currentUser));
            loadDashboard();
        } else {
            showError('login-error', result.message);
        }
    });

    // Signup
    document.getElementById('signup-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('signup-username').value;
        const password = document.getElementById('signup-password').value;
        
        const result = await apiCall('/signup', 'POST', { username, password });
        
        if (result.success) {
            currentUser = result.user;
            localStorage.setItem('wakeyUser', JSON.stringify(currentUser));
            loadDashboard();
        } else {
            showError('signup-error', result.message);
        }
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('wakeyUser');
        currentUser = null;
        showScreen('auth-screen');
    });

    // Dashboard tabs
    document.querySelectorAll('.dash-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.dash-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            const viewId = tab.dataset.view + '-view';
            showView(viewId);
            
            if (tab.dataset.view === 'friends') {
                loadFriends();
            } else if (tab.dataset.view === 'requests') {
                loadFriendRequests();
            }
        });
    });

    // Modal close buttons
    document.querySelectorAll('.close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.remove('active');
        });
    });

    // Create alarm button
    document.getElementById('create-alarm-btn').addEventListener('click', () => {
        loadFriendsForAlarm();
        showModal('create-alarm-modal');
    });

    // Create alarm form
    document.getElementById('create-alarm-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const friendId = parseInt(document.getElementById('alarm-friend-select').value);
        const time = document.getElementById('alarm-time').value;
        const label = document.getElementById('alarm-label').value;
        const sound = document.getElementById('alarm-sound').value;
        const tone = document.getElementById('alarm-tone').value || null;
        
        if (!friendId) {
            alert('Please select a friend');
            return;
        }
        
        const result = await apiCall('/alarms', 'POST', {
            userId: currentUser.id,
            friendId,
            time,
            label,
            sound,
            tone
        });
        
        if (result.success) {
            closeModal('create-alarm-modal');
            document.getElementById('create-alarm-form').reset();
            // Reload friends list to ensure we have names
            await loadFriends();
            // Then reload alarms
            await loadAlarms();
            alert('Alarm created successfully! 🎉');
        } else {
            alert(result.message);
        }
    });

    // Search users button
    document.getElementById('search-users-btn').addEventListener('click', () => {
        showModal('search-users-modal');
        document.getElementById('user-search-input').value = '';
        document.getElementById('search-results').innerHTML = '<p class="empty-state">Start typing to search...</p>';
    });

    // User search
    let searchTimeout;
    document.getElementById('user-search-input').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        
        if (!query) {
            document.getElementById('search-results').innerHTML = '<p class="empty-state">Start typing to search...</p>';
            return;
        }
        
        searchTimeout = setTimeout(async () => {
            const users = await apiCall(`/users/search?query=${query}&currentUserId=${currentUser.id}`);
            displaySearchResults(users);
        }, 300);
    });

    // Alarm actions
    document.getElementById('alarm-snooze-btn').addEventListener('click', () => handleAlarmAction('snooze'));
    document.getElementById('alarm-acknowledge-btn').addEventListener('click', () => handleAlarmAction('acknowledge'));
    document.getElementById('alarm-cancel-btn').addEventListener('click', () => handleAlarmAction('cancel'));
});

// ==================== DASHBOARD ====================
async function loadDashboard() {
    showScreen('dashboard-screen');
    document.getElementById('username-display').textContent = currentUser.username;
    // Load friends first so we have the names
    await loadFriends();
    // Then load alarms
    await loadAlarms();
}

async function loadAlarms() {
    try {
        alarms = await apiCall(`/alarms/${currentUser.id}`);
        console.log('Loaded alarms:', alarms); // Debug log
        displayAlarms();
    } catch (error) {
        console.error('Error loading alarms:', error);
    }
}

function displayAlarms() {
    const list = document.getElementById('alarms-list');
    
    console.log('Displaying alarms:', alarms); // Debug log
    console.log('Friends list:', friends); // Debug log
    
    if (!alarms || alarms.length === 0) {
        list.innerHTML = '<p class="empty-state">No alarms yet. Create one with a friend!</p>';
        return;
    }
    
    list.innerHTML = alarms.map(alarm => {
        const partnerId = alarm.user1Id === currentUser.id ? alarm.user2Id : alarm.user1Id;
        const partnerName = getPartnerName(partnerId);
        const partnerInitial = partnerName.charAt(0).toUpperCase();
        
        console.log('Alarm:', alarm, 'Partner:', partnerId, partnerName); // Debug log
        
        return `
            <div class="alarm-card">
                <div class="alarm-info">
                    <h4>${alarm.time}</h4>
                    <p>${alarm.label}</p>
                    <span class="alarm-badge">with ${partnerName}</span>
                    <span class="alarm-badge">🔊 ${alarm.sound}</span>
                </div>
                <div class="alarm-actions-card">
                    <div class="friend-avatar" style="width: 42px; height: 42px; font-size: 18px;">
                        ${partnerInitial}
                    </div>
                    <button class="btn-icon" onclick="testAlarm(${alarm.id})" title="Test Alarm">🔔</button>
                </div>
            </div>
        `;
    }).join('');
}

function getPartnerName(partnerId) {
    // Try to find in friends list
    const friend = friends.find(f => f.id === partnerId);
    return friend ? friend.username : 'Friend';
}

// ==================== FRIENDS ====================
async function loadFriends() {
    friends = await apiCall(`/friends/${currentUser.id}`);
    displayFriends();
}

function displayFriends() {
    const list = document.getElementById('friends-list');
    
    if (friends.length === 0) {
        list.innerHTML = '<p class="empty-state">No friends yet. Add some to create shared alarms!</p>';
        return;
    }
    
    list.innerHTML = friends.map(friend => `
        <div class="friend-card">
            <div class="friend-info">
                <div class="friend-avatar">${friend.username.charAt(0).toUpperCase()}</div>
                <span class="friend-name">${friend.username}</span>
            </div>
        </div>
    `).join('');
}

async function loadFriendRequests() {
    const requests = await apiCall(`/friends/requests/${currentUser.id}`);
    
    const container = document.getElementById('friend-requests-list');
    
    if (requests.length === 0) {
        container.innerHTML = '<p class="empty-state">No pending friend requests</p>';
        return;
    }
    
    container.innerHTML = requests.map(req => `
        <div class="request-card">
            <div class="friend-info">
                <div class="friend-avatar">${req.fromUsername.charAt(0).toUpperCase()}</div>
                <span class="friend-name">${req.fromUsername}</span>
            </div>
            <div class="request-actions">
                <button class="btn-accept" onclick="acceptFriendRequest(${req.id})">Accept</button>
            </div>
        </div>
    `).join('');
}

async function acceptFriendRequest(requestId) {
    const result = await apiCall('/friends/accept', 'POST', {
        requestId,
        userId: currentUser.id
    });
    
    if (result.success) {
        loadFriendRequests();
        loadFriends();
    }
}

async function loadFriendsForAlarm() {
    if (friends.length === 0) {
        friends = await apiCall(`/friends/${currentUser.id}`);
    }
    
    const select = document.getElementById('alarm-friend-select');
    select.innerHTML = '<option value="">Select a friend...</option>' + 
        friends.map(f => `<option value="${f.id}">${f.username}</option>`).join('');
}

// ==================== SEARCH ====================
function displaySearchResults(users) {
    const results = document.getElementById('search-results');
    
    if (users.length === 0) {
        results.innerHTML = '<p class="empty-state">No users found</p>';
        return;
    }
    
    results.innerHTML = users.map(user => `
        <div class="search-result-item">
            <span>${user.username}</span>
            <button class="btn btn-primary btn-small" onclick="sendFriendRequest(${user.id})">
                Add Friend
            </button>
        </div>
    `).join('');
}

async function sendFriendRequest(toUserId) {
    const result = await apiCall('/friends/request', 'POST', {
        fromUserId: currentUser.id,
        toUserId
    });
    
    alert(result.message);
    
    if (result.success) {
        closeModal('search-users-modal');
    }
}

// ==================== ALARM RINGING ====================
function testAlarm(alarmId) {
    currentAlarm = alarms.find(a => a.id === alarmId);
    if (!currentAlarm) return;
    
    const partnerId = currentAlarm.user1Id === currentUser.id ? currentAlarm.user2Id : currentAlarm.user1Id;
    const partnerName = getPartnerName(partnerId);
    
    document.getElementById('alarm-ringing-label').textContent = currentAlarm.label;
    document.getElementById('alarm-ringing-time').textContent = currentAlarm.time;
    document.getElementById('alarm-partner-name').textContent = partnerName;
    
    updateAlarmDisplay();
    
    // Play alarm sound
    playAlarmSound(currentAlarm.sound);
    
    showModal('alarm-ringing-modal');
}

function playAlarmSound(soundName) {
    console.log('Trying to play sound:', soundName); // Debug log
    
    // Stop any currently playing alarm
    if (alarmAudio) {
        alarmAudio.pause();
        alarmAudio.currentTime = 0;
    }
    
    // Create new audio instance
    const audioPath = `audio/${soundName}.mp3`;
    console.log('Audio path:', audioPath); // Debug log
    
    alarmAudio = new Audio(audioPath);
    alarmAudio.loop = true; // Loop the alarm sound
    alarmAudio.volume = 0.7; // 70% volume
    
    // Play the sound
    alarmAudio.play()
        .then(() => {
            console.log('Audio playing successfully!');
        })
        .catch(err => {
            console.error('Audio play failed:', err);
            alert('Could not play alarm sound. Using beep instead.');
            // Fallback: use default beep sound
            playDefaultBeep();
        });
}

function playDefaultBeep() {
    // Create a simple beep using Web Audio API
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = 800; // 800 Hz beep
    oscillator.type = 'sine';
    
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.3); // 0.3 second beep
    
    // Repeat beep every second
    alarmAudio = setInterval(() => {
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        
        osc.connect(gain);
        gain.connect(audioContext.destination);
        
        osc.frequency.value = 800;
        osc.type = 'sine';
        gain.gain.setValueAtTime(0.3, audioContext.currentTime);
        
        osc.start(audioContext.currentTime);
        osc.stop(audioContext.currentTime + 0.3);
    }, 1000);
}

function stopAlarmSound() {
    if (alarmAudio) {
        if (alarmAudio instanceof Audio) {
            alarmAudio.pause();
            alarmAudio.currentTime = 0;
        } else {
            // It's an interval (beep)
            clearInterval(alarmAudio);
        }
        alarmAudio = null;
    }
}

function updateAlarmDisplay() {
    const userSnoozes = currentAlarm.snoozeCount[currentUser.id] || 0;
    const partnerId = currentAlarm.user1Id === currentUser.id ? currentAlarm.user2Id : currentAlarm.user1Id;
    const partnerSnoozes = currentAlarm.snoozeCount[partnerId] || 0;
    
    document.getElementById('user-snooze-count').textContent = userSnoozes;
    document.getElementById('friend-snooze-count').textContent = partnerSnoozes;
    
    const messageContainer = document.getElementById('agent-message-container');
    
    if (currentAlarm.agentMessage) {
        messageContainer.textContent = currentAlarm.agentMessage;
        messageContainer.className = `agent-message ${currentAlarm.agentTone || ''}`;
    } else {
        messageContainer.textContent = 'Time to wake up! ⏰';
        messageContainer.className = 'agent-message';
    }
    
    // Show cancel notification if friend cancelled
    if (currentAlarm.cancelledBy && currentAlarm.cancelledBy !== currentUser.id) {
        messageContainer.textContent = currentAlarm.cancelNotifyMessage || 'Your friend cancelled the alarm';
        messageContainer.className = 'agent-message playful';
    }
}

async function handleAlarmAction(action) {
    // Stop the alarm sound
    stopAlarmSound();
    
    const result = await apiCall(`/agent/${action}`, 'POST', {
        alarmId: currentAlarm.id,
        userId: currentUser.id
    });
    
    if (result.success) {
        currentAlarm = result.alarm;
        updateAlarmDisplay();
        
        // Close modal if acknowledged by both or cancelled
        if (action === 'acknowledge' && currentAlarm.acknowledged.length === 2) {
            setTimeout(() => {
                closeModal('alarm-ringing-modal');
                loadAlarms();
            }, 2000);
        }
        
        if (action === 'cancel') {
            setTimeout(() => {
                closeModal('alarm-ringing-modal');
                loadAlarms();
            }, 2000);
        }
        
        // If snoozed, play sound again after showing message
        if (action === 'snooze') {
            setTimeout(() => {
                playAlarmSound(currentAlarm.sound);
            }, 3000); // Play again after 3 seconds
        }
    }
}

// Make functions global for onclick handlers
window.testAlarm = testAlarm;
window.acceptFriendRequest = acceptFriendRequest;
window.sendFriendRequest = sendFriendRequest;
// ==================== AUTOMATIC ALARM CHECKING ====================
// Check every minute if any alarm should ring
setInterval(() => {
    if (!currentUser || alarms.length === 0) return;
    
    const now = new Date();
    const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    // Find alarms that match current time and are active
    const alarmsToRing = alarms.filter(alarm => {
        return alarm.time === currentTime && 
               alarm.status === 'active' && 
               !alarm.hasRungToday; // Prevent ringing multiple times
    });
    
    // Trigger each alarm
    alarmsToRing.forEach(alarm => {
        alarm.hasRungToday = true; // Mark as rung
        testAlarm(alarm.id);
    });
    
    // Reset hasRungToday at midnight
    if (currentTime === '00:00') {
        alarms.forEach(alarm => alarm.hasRungToday = false);
    }
}, 60000); // Check every 60 seconds (1 minute)

// Also check immediately when page loads (in case alarm time was missed)
setTimeout(() => {
    if (!currentUser || alarms.length === 0) return;
    
    const now = new Date();
    const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    alarms.filter(alarm => alarm.time === currentTime && alarm.status === 'active')
          .forEach(alarm => testAlarm(alarm.id));
}, 2000); // Check 2 seconds after page load