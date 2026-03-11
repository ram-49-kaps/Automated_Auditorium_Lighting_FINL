/**
 * Main viewer logic for lighting visualization
 */

let currentState = {
    is_playing: false,
    elapsed_time: 0,
    total_duration: 0,
    current_cue: null
};

let allCues = [];
let allFixtures = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🎭 Initializing Lighting Visualizer...');
    
    await loadCues();
    await loadFixtures();
    setupControls();
    setupWebSocket();
    startStatePolling();
});

// Load cues from API
async function loadCues() {
    try {
        const response = await fetch('/api/cues');
        const data = await response.json();
        allCues = data.cues || [];
        
        console.log(`✅ Loaded ${allCues.length} cues`);
        renderCueList();
        updateTotalTime();
    } catch (err) {
        console.error('Failed to load cues:', err);
    }
}

// Load fixtures from API
async function loadFixtures() {
    try {
        const response = await fetch('/api/fixtures');
        const data = await response.json();
        allFixtures = data.fixtures || [];
        
        console.log(`✅ Loaded ${allFixtures.length} fixtures`);
        renderFixtures();
    } catch (err) {
        console.error('Failed to load fixtures:', err);
    }
}

// Setup control buttons
function setupControls() {
    document.getElementById('playBtn').addEventListener('click', play);
    document.getElementById('pauseBtn').addEventListener('click', pause);
    document.getElementById('stopBtn').addEventListener('click', stop);
    
    const seekBar = document.getElementById('seekBar');
    seekBar.addEventListener('input', (e) => {
        const percent = parseFloat(e.target.value);
        const time = (percent / 100) * currentState.total_duration;
        seek(time);
    });
}

// Setup WebSocket listener
function setupWebSocket() {
    wsClient.on((message) => {
        if (message.type === 'playback_update') {
            updateState(message.data);
        }
    });
}

// Poll state from API (backup to WebSocket)
function startStatePolling() {
    setInterval(async () => {
        try {
            const response = await fetch('/api/playback/state');
            const state = await response.json();
            updateState(state);
        } catch (err) {
            // Ignore errors if WebSocket is working
        }
    }, 200);
}

// Playback controls
async function play() {
    await fetch('/api/playback/play', { method: 'POST' });
}

async function pause() {
    await fetch('/api/playback/pause', { method: 'POST' });
}

async function stop() {
    await fetch('/api/playback/stop', { method: 'POST' });
}

async function seek(timeSeconds) {
    await fetch(`/api/playback/seek/${timeSeconds}`, { method: 'POST' });
}

// Update UI state
function updateState(state) {
    currentState = state;
    
    // Update time display
    document.getElementById('currentTime').textContent = formatTime(state.elapsed_time);
    
    // Update seek bar
    const seekBar = document.getElementById('seekBar');
    seekBar.value = state.progress || 0;
    
    // Update progress fill
    document.getElementById('progressFill').style.width = `${state.progress || 0}%`;
    
    // Update playback status
    const statusEl = document.getElementById('playbackStatus');
    if (state.is_playing && !state.is_paused) {
        statusEl.textContent = '▶ Playing';
    } else if (state.is_paused) {
        statusEl.textContent = '⏸ Paused';
    } else {
        statusEl.textContent = '⏹ Stopped';
    }
    
    // Update current scene info
    if (state.current_cue) {
        updateSceneInfo(state.current_cue);
        updateFixtureStates(state.current_cue);
        highlightActiveCue(state.current_cue);
    } else {
        clearSceneInfo();
    }
}

// Update scene information
function updateSceneInfo(cue) {
    document.getElementById('sceneId').textContent = cue.scene_id || '-';
    
    const emotionEl = document.getElementById('emotion');
    const emotion = cue.emotion || 'neutral';
    emotionEl.textContent = emotion.toUpperCase();
    emotionEl.className = `value emotion-badge emotion-${emotion}`;
    
    const duration = cue.end_time - cue.start_time;
    document.getElementById('duration').textContent = `${duration.toFixed(1)}s`;
    
    const transition = cue.cues && cue.cues.length > 0 
        ? cue.cues[0].transition_type 
        : '-';
    document.getElementById('transition').textContent = transition;
}

// Clear scene info
function clearSceneInfo() {
    document.getElementById('sceneId').textContent = '-';
    document.getElementById('emotion').textContent = '-';
    document.getElementById('emotion').className = 'value emotion-badge';
    document.getElementById('duration').textContent = '-';
    document.getElementById('transition').textContent = '-';
}

// Update fixture visual states
function updateFixtureStates(cue) {
    if (!cue.cues) return;
    
    cue.cues.forEach(fixtureCue => {
        const fixtureId = fixtureCue.fixture_id;
        const lightEl = document.querySelector(`[data-fixture-id="${fixtureId}"] .fixture-light`);
        const colorNameEl = document.querySelector(`[data-fixture-id="${fixtureId}"] .color-name`);
        const intensityEl = document.querySelector(`[data-fixture-id="${fixtureId}"] .intensity`);
        
        if (lightEl && fixtureCue.dmx_channels) {
            // Get RGB values
            const channels = fixtureCue.dmx_channels;
            const r = parseInt(channels['1']) || 0;
            const g = parseInt(channels['2']) || 0;
            const b = parseInt(channels['3']) || 0;
            const intensity = parseInt(channels['8']) || 0;
            
            // Set color
            const color = `rgb(${r}, ${g}, ${b})`;
            lightEl.style.backgroundColor = color;
            lightEl.style.opacity = intensity / 255;
            
            if (intensity > 0) {
                lightEl.classList.add('active');
            } else {
                lightEl.classList.remove('active');
            }
            
            // Update text
            if (colorNameEl) {
                colorNameEl.textContent = getColorName(r, g, b);
            }
            
            if (intensityEl) {
                const percent = Math.round((intensity / 255) * 100);
                intensityEl.textContent = `${percent}%`;
            }
        }
    });
}

// Highlight active cue in list
function highlightActiveCue(cue) {
    document.querySelectorAll('.cue-item').forEach(el => {
        el.classList.remove('active');
    });
    
    const activeEl = document.querySelector(`[data-scene-id="${cue.scene_id}"]`);
    if (activeEl) {
        activeEl.classList.add('active');
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Render fixtures grid
function renderFixtures() {
    const container = document.getElementById('fixturesContainer');
    container.innerHTML = '';
    
    allFixtures.forEach(fixture => {
        const card = document.createElement('div');
        card.className = 'fixture-card';
        card.setAttribute('data-fixture-id', fixture.id);
        
        card.innerHTML = `
            <div class="fixture-name">${fixture.name || fixture.id}</div>
            <div class="fixture-light" style="background-color: #333;"></div>
            <div class="fixture-info">
                <span class="color-name">Off</span>
                <span class="intensity">0%</span>
            </div>
        `;
        
        container.appendChild(card);
    });
}

// Render cue list
function renderCueList() {
    const container = document.getElementById('cueListContainer');
    container.innerHTML = '';
    
    allCues.forEach(cue => {
        const item = document.createElement('div');
        item.className = 'cue-item';
        item.setAttribute('data-scene-id', cue.scene_id);
        
        const emotion = cue.emotion || 'neutral';
        
        item.innerHTML = `
            <span class="cue-time">${formatTime(cue.start_time)}</span>
            <span class="cue-scene">${cue.scene_id}</span>
            <span class="cue-emotion emotion-badge emotion-${emotion}">${emotion}</span>
        `;
        
        item.addEventListener('click', () => {
            seek(cue.start_time);
        });
        
        container.appendChild(item);
    });
}

// Update total time display
function updateTotalTime() {
    if (allCues.length > 0) {
        const maxTime = Math.max(...allCues.map(c => c.end_time || 0));
        document.getElementById('totalTime').textContent = formatTime(maxTime);
    }
}

// Helper: Format time (seconds to MM:SS)
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Helper: Get color name from RGB
function getColorName(r, g, b) {
    const brightness = (r + g + b) / 3;
    
    if (brightness < 20) return 'Off';
    if (r > 200 && g > 200 && b > 200) return 'White';
    if (r > 200 && g < 50 && b < 50) return 'Red';
    if (r < 50 && g > 200 && b < 50) return 'Green';
    if (r < 50 && g < 50 && b > 200) return 'Blue';
    if (r > 150 && g > 100 && b < 50) return 'Orange';
    if (r > 200 && g > 150 && b < 50) return 'Yellow';
    
    return 'Mixed';
}