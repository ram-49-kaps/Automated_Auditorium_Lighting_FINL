
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Configuration
const CONFIG = {
    stage: { width: 16, depth: 10, height: 1.0 },
    auditorium: { width: 20, depth: 20, height: 8 }
};

// Default Colors
const FIXTURE_DEFAULTS = {
    blinder: { color: new THREE.Color(1, 0.7, 0.3), hasRGB: false },
    profile: { color: new THREE.Color(1, 0.95, 0.8), hasRGB: false },
    fresnel: { color: new THREE.Color(1, 0.95, 0.8), hasRGB: false },
    par: { color: new THREE.Color(1, 0.95, 0.8), hasRGB: false },
    par_rgb: { color: new THREE.Color(1, 1, 1), hasRGB: true },
    moving_head: { color: new THREE.Color(1, 1, 1), hasRGB: true },
    smoke_machine: { color: null, hasRGB: false, isSmoke: true }
};

const RGB_COLORS = {
    red: new THREE.Color(1, 0, 0),
    green: new THREE.Color(0, 1, 0),
    blue: new THREE.Color(0, 0, 1),
    white: new THREE.Color(1, 1, 1)
};

// Shape Geometries
const Geometries = {
    profile: () => {
        const g = new THREE.Group();
        const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 0.7, 12), new THREE.MeshLambertMaterial({ color: 0x1a1a1a }));
        barrel.rotation.x = Math.PI / 2;
        const hood = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.06, 0.15, 12), new THREE.MeshLambertMaterial({ color: 0x222222 }));
        hood.rotation.x = Math.PI / 2; hood.position.z = 0.4;
        const yoke = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.25, 0.02), new THREE.MeshLambertMaterial({ color: 0x333333 }));
        yoke.position.y = 0.15;
        g.add(barrel, hood, yoke);
        return g;
    },
    fresnel: () => {
        const g = new THREE.Group();
        const body = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.25), new THREE.MeshLambertMaterial({ color: 0x1a1a1a }));
        const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.03, 16), new THREE.MeshLambertMaterial({ color: 0x333333 }));
        lens.rotation.x = Math.PI / 2; lens.position.z = 0.14;
        const topDoor = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.02, 0.1), new THREE.MeshLambertMaterial({ color: 0x111111 }));
        topDoor.position.set(0, 0.16, 0.1);
        const bottomDoor = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.02, 0.1), new THREE.MeshLambertMaterial({ color: 0x111111 }));
        bottomDoor.position.set(0, -0.16, 0.1);
        g.add(body, lens, topDoor, bottomDoor);
        return g;
    },
    blinder: () => {
        const g = new THREE.Group();
        const body = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.15), new THREE.MeshLambertMaterial({ color: 0x1a1a1a }));
        [[-0.12, 0.12], [0.12, 0.12], [-0.12, -0.12], [0.12, -0.12]].forEach(pos => {
            const cell = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.08, 8), new THREE.MeshLambertMaterial({ color: 0x444444 }));
            cell.rotation.x = Math.PI / 2; cell.position.set(pos[0], pos[1], 0.08);
            g.add(cell);
        });
        g.add(body);
        return g;
    },
    par: () => {
        const g = new THREE.Group();
        const can = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.2, 12), new THREE.MeshLambertMaterial({ color: 0x1a1a1a }));
        can.rotation.x = Math.PI / 2;
        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.015, 8, 16), new THREE.MeshLambertMaterial({ color: 0x333333 }));
        ring.position.z = 0.1;
        g.add(can, ring);
        return g;
    },
    moving_head: () => {
        const g = new THREE.Group();
        const base = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.08, 0.25), new THREE.MeshLambertMaterial({ color: 0x1a1a1a }));
        const leftArm = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.3, 0.05), new THREE.MeshLambertMaterial({ color: 0x222222 }));
        leftArm.position.set(-0.1, 0.15, 0);
        const rightArm = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.3, 0.05), new THREE.MeshLambertMaterial({ color: 0x222222 }));
        rightArm.position.set(0.1, 0.15, 0);
        const head = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.25, 12), new THREE.MeshLambertMaterial({ color: 0x1a1a1a }));
        head.rotation.x = Math.PI / 2; head.position.y = 0.25;
        const lens = new THREE.Mesh(new THREE.CircleGeometry(0.07, 16), new THREE.MeshBasicMaterial({ color: 0x222222 }));
        lens.position.set(0, 0.25, 0.13);
        g.add(base, leftArm, rightArm, head, lens);
        return g;
    },
    smoke_machine: () => {
        const g = new THREE.Group();
        const body = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.25, 0.6), new THREE.MeshLambertMaterial({ color: 0x2a2a2a }));
        const nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.08, 0.15, 8), new THREE.MeshLambertMaterial({ color: 0x444444 }));
        nozzle.rotation.x = Math.PI / 2; nozzle.position.z = 0.35;
        g.add(body, nozzle);
        return g;
    }
};

class AuditoriumSimulation {
    constructor() {
        this.canvas = document.createElement('canvas');
        document.body.appendChild(this.canvas);
        document.getElementById('loading').style.display = 'none';

        this.smokeParticles = null;
        this.smokeActive = false;

        this.initScene();
        this.initAssets();
        this.buildArchitecture();

        // Use new advanced smoke
        this.initSmoke();

        this.initLightingRig();
        this.initNetwork();
        this.animate();

        window.addEventListener('resize', () => this.onResize());
        window.sim = this;
    }

    initNetwork() {
        console.log("Connecting to Lighting Console...");
        this.socket = new WebSocket('ws://16.171.153.178:8765');

        // Expose sendCommand to global scope for HTML buttons
        window.sendCommand = (cmd, val) => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                const payload = { command: cmd };
                if (cmd === 'JUMP') payload.index = val;
                if (cmd === 'START_SIM') payload.endMode = val;
                this.socket.send(JSON.stringify(payload));
            }
        };

        // Expose changeTheme for the new live-edit feature
        window.changeTheme = (event, cueIndex) => {
            event.stopPropagation(); // prevent clicking from triggering JUMP
            const newTheme = event.target.value;
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({
                    command: 'THEME',
                    index: cueIndex,
                    theme: newTheme
                }));
            }
        };

        this.socket.onopen = () => {
            console.log("✅ CONNECTED to Console");
        };

        this.socket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);

                if (msg.type === 'state_update') {
                    this.renderConsole(msg);
                    if (msg.scene_data) {
                        this.applyScene(msg.scene_data);
                    }
                }
            } catch (e) {
                console.error("Msg Error:", e);
            }
        };

        this.socket.onclose = () => {
            console.log("❌ DISCONNECTED");
            setTimeout(() => this.initNetwork(), 3000);
        };
    }

    renderConsole(state) {
        // Parse transitions for smooth fade-ins and dynamic cueing
        this.currentTransitionType = state.transition_type || 'fade';
        this.currentTransitionDuration = typeof state.transition_duration === 'number' ? state.transition_duration : 2.0;

        const list = document.getElementById('cueList');
        if (!list) return;

        let html = '';

        // Using context_window from server
        if (state.context_window) {
            const allThemes = ["JOY", "FEAR", "ANGER", "SADNESS", "SURPRISE", "DISGUST", "NEUTRAL",
                "NOSTALGIA", "MYSTERY", "ROMANTIC", "ANTICIPATION", "HOPE", "TRIUMPH",
                "TENSION", "DESPAIR", "SERENITY", "CONFUSION", "AWE", "JEALOUSY"];

            state.context_window.forEach(cue => {
                const activeStart = cue.active ? 'active' : '';

                // Create Theme Dropdown instead of static badge
                let sceneSelect = '';
                if (cue.scene) {
                    const options = allThemes.map(t =>
                        `<option value="${t}" ${cue.scene.toUpperCase() === t ? 'selected' : ''}>${t}</option>`
                    ).join('');

                    sceneSelect = `
                        <select class="theme-selector" onclick="event.stopPropagation()" onchange="changeTheme(event, ${cue.id})">
                            ${options}
                        </select>
                    `;
                }

                const isActive = activeStart === 'active';
                const clickAction = `onclick="sendCommand('JUMP', ${cue.id})"`;
                // Parse scene_id from the display text format "scene_XXX │ EMOTION │ text"
                const parts = (cue.text || '').split('│');
                const sceneId = parts[0] ? parts[0].trim() : `scene_${String(cue.id + 1).padStart(3, '0')}`;

                // Scene ID badge
                const sceneIdBadge = `<span class="cue-scene-id">${sceneId}</span>`;

                if (isActive) {
                    // Active cue: rendering text block
                    let contentHtml = '';

                    if (cue.dialogue_lines && cue.dialogue_lines.length > 0) {
                        contentHtml += '<div class="system-msg" style="color:#00d4ff; font-family:monospace; margin-bottom:8px;">[System] Fade In</div>';
                        contentHtml += `<div class="scene-id" style="color:#a855f7; font-weight:bold; margin-bottom:12px;">${sceneId}</div>`;

                        cue.dialogue_lines.forEach(dl => {
                            contentHtml += `<div class="dialogue-line" style="margin-bottom:8px;">
                                <strong style="color:#fbbf24; margin-right:8px;">${dl.character}:</strong>
                                <span>${dl.line}</span>
                            </div>`;
                        });

                        contentHtml += '<div class="system-msg" style="color:#00d4ff; font-family:monospace; margin-top:12px;">[System] Fade Out</div>';
                    } else {
                        const fullText = cue.script_full || cue.script_line || '';
                        contentHtml = fullText.replace(/\n/g, '<br>');
                    }

                    html += `<div class="cue-item active" ${clickAction}>
                                <div class="cue-header-row">
                                    ${sceneIdBadge}
                                    <span class="cue-separator">│</span>
                                    <span class="cue-preview">${cue.script_line || ''}</span>
                                    ${sceneSelect}
                                </div>
                                <div class="cue-full-text">${contentHtml}</div>
                             </div>`;
                } else {
                    // Inactive cue: compact — scene_id | short preview | dropdown
                    html += `<div class="cue-item" ${clickAction}>
                                <span class="cue-num">${cue.id + 1}.</span>
                                ${sceneIdBadge}
                                <span class="cue-separator">│</span>
                                <span class="cue-preview">${cue.script_line || ''}</span>
                                ${sceneSelect}
                             </div>`;
                }
            });
        }

        list.innerHTML = html;
        const activeItem = list.querySelector('.active');
        if (activeItem && !this.userScrolled) {
            activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        // Button State
        const btnHold = document.getElementById('btnHold');
        if (btnHold) {
            if (state.is_holding) {
                btnHold.classList.add('active');
                btnHold.innerText = "RESUME ▶";
            } else {
                btnHold.classList.remove('active');
                btnHold.innerText = "⏸ HOLD";
            }
        }

        // NEXT / FINISH Button State
        const btnNext = document.querySelector('.btn-next');
        if (btnNext && typeof state.total_cues !== 'undefined') {
            if (state.current_index >= state.total_cues - 1) {
                btnNext.innerText = "FINISH 🏁";
                btnNext.style.backgroundColor = "#ffba08";
                btnNext.style.color = "#000";
                btnNext.onclick = () => {
                    const fbOverlay = document.getElementById("feedbackOverlay");
                    if (fbOverlay) fbOverlay.style.display = "flex";
                };
            } else {
                btnNext.innerText = "GO ⏭";
                btnNext.style.backgroundColor = ""; // Reset to default CSS
                btnNext.style.color = "";
                btnNext.onclick = () => {
                    if (window.sendCommand) window.sendCommand('NEXT');
                };
            }
        }

        // Progress Bar Update
        const fill = document.getElementById('progressBarFill');
        const text = document.getElementById('progressText');
        const bg = document.getElementById('progressBarBg');
        if (fill && text && typeof state.total_cues !== 'undefined') {
            const total = state.total_cues > 0 ? state.total_cues : 1;
            const current = state.current_index;

            // Use time-based progress if available, else fallback to index-based
            let pct;
            if (state.total_duration && state.total_duration > 0 && typeof state.sim_elapsed === 'number') {
                pct = (state.sim_elapsed / state.total_duration) * 100;
            } else {
                pct = (current / (total - 1)) * 100;
            }
            fill.style.width = `${Math.min(100, Math.max(0, pct))}%`;

            // Show simulation clock if available
            if (state.sim_clock && state.total_clock) {
                text.innerText = `${state.sim_clock} / ${state.total_clock}`;
            } else {
                text.innerText = `${current + 1} / ${total}`;
            }

            // Inject markers the first time we know the total
            if (bg.children.length <= 1 && total > 1) { // 1 child is the fill bar
                for (let i = 0; i < total; i++) {
                    const marker = document.createElement('div');
                    marker.className = 'progress-marker';
                    marker.style.left = `${(i / (total - 1)) * 100}%`;
                    if (i === total - 1) marker.style.left = 'calc(100% - 4px)';
                    bg.appendChild(marker);
                }
            }

            // Allow clicking progress bar to jump
            bg.onclick = (e) => {
                const rect = bg.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const clickPct = clickX / rect.width;
                const targetIdx = Math.round(clickPct * (total - 1));
                if (window.sendCommand) {
                    window.sendCommand('JUMP', targetIdx);
                }
            };
        }

        // Use server-sent elapsed time for teleprompter
        if (typeof state.elapsed === 'number') {
            state._cue_elapsed = state.elapsed;
        } else if (!this.latestState || this.latestState.current_index !== state.current_index) {
            state._cue_elapsed = 0;
        } else {
            state._cue_elapsed = this.latestState._cue_elapsed || 0;
        }
        this.latestState = state;

        // ── TELEPROMPTER UPDATE ──
        this.updateTeleprompter(state);
    }

    updateTeleprompter(state) {
        const tpText = document.getElementById('tpText');
        const tpTag = document.getElementById('tpSceneTag');
        if (!tpText || !tpTag) return;

        // Find the active cue
        const activeCue = state.context_window
            ? state.context_window.find(c => c.active)
            : null;

        if (!activeCue) {
            tpText.innerHTML = '<span class="word upcoming">Waiting for cue...</span>';
            tpTag.textContent = '';
            return;
        }

        const fullText = activeCue.script_full || activeCue.script_line || '';
        const sceneId = `scene_${String(activeCue.id + 1).padStart(3, '0')}`;
        const emotion = (activeCue.scene || 'NEUTRAL').toUpperCase();
        tpTag.textContent = `${sceneId} • ${emotion}`;

        // Split text into words
        const words = fullText.split(/\s+/).filter(w => w.length > 0);
        if (words.length === 0) {
            tpText.innerHTML = '';
            return;
        }

        // Calculate progress: elapsed / duration
        const elapsed = state._cue_elapsed || state.elapsed || 0;
        const duration = activeCue.duration || 30;
        const progress = Math.min(1.0, elapsed / duration);

        // Current word index based on progress
        const currentWordIdx = Math.floor(progress * words.length);

        // Only rebuild DOM if cue changed (tracked by data attribute)
        const cueKey = `${activeCue.id}-${words.length}`;
        if (tpText.dataset.cueKey !== cueKey) {
            tpText.dataset.cueKey = cueKey;
            tpText.innerHTML = words.map((word, i) =>
                `<span class="word upcoming" data-idx="${i}">${word} </span>`
            ).join('');
        }

        // Update word classes
        const wordEls = tpText.querySelectorAll('.word');
        wordEls.forEach((el, i) => {
            el.className = 'word';
            if (i < currentWordIdx) {
                el.classList.add('spoken');
            } else if (i === currentWordIdx) {
                el.classList.add('current');
            } else {
                el.classList.add('upcoming');
            }
        });

        // Smooth auto-scroll to keep current word visible and centered
        const currentEl = tpText.querySelector('.word.current');
        if (currentEl) {
            const containerRect = tpText.getBoundingClientRect();
            const wordRect = currentEl.getBoundingClientRect();
            // Calculate where we want to scroll to (center the word)
            const scrollTopTarget = tpText.scrollTop + (wordRect.top - containerRect.top) - (containerRect.height / 2) + (wordRect.height / 2);

            // Smoothly lerp the scroll position instead of native scrollIntoView which can be jagged
            if (Math.abs(tpText.scrollTop - scrollTopTarget) > 1) {
                tpText.scrollTop += (scrollTopTarget - tpText.scrollTop) * 0.1; // Smooth lerp logic
            }
        }
    }

    updateFixtureStatusUI() {
        const list = document.getElementById('fixtureList');
        if (!list) return;

        let html = '';
        const groups = {};

        Object.values(this.fixtures).forEach(mesh => {
            const groupKey = mesh.userData.groupId || mesh.userData.location;
            if (!groups[groupKey]) groups[groupKey] = [];
            groups[groupKey].push(mesh);
        });

        Object.keys(groups).sort().forEach(groupName => {
            html += `<div class="f-group">${groupName}</div>`;
            groups[groupName].forEach(mesh => {
                const intensity = Math.round(mesh.userData.intensity);
                let colorHex = '#000000';
                if (mesh.userData.config.hasRGB) {
                    colorHex = '#' + mesh.userData.color.getHexString();
                } else if (intensity > 0) {
                    colorHex = '#FFFFFF'; // Warm white usually
                }

                const styleDot = `display:inline-block; width:10px; height:10px; background:${colorHex}; border-radius:50%; margin-right:5px;`;

                html += `<div class="fixture-row">
                            <span>${mesh.userData.fixtureId}</span>
                            <span class="fixture-val"><span style="${styleDot}"></span> ${intensity}%</span>
                         </div>`;
            });
        });
        list.innerHTML = html;
    }

    applyScene(settings) {
        // The server sends keys like "FOH_FRESNEL", "FOH_PROFILE", "STAGE_BLINDER", 
        // "FOH_MOVING", "STAGE_RGB_PAR". We match each fixture ID against these prefixes.
        const settingKeys = Object.keys(settings).filter(k => k !== 'SMOKE');

        Object.keys(this.fixtures).forEach(fid => {
            const mesh = this.fixtures[fid];

            // Find the matching setting key by checking if the fixture ID starts with it
            let matchedData = null;
            for (const key of settingKeys) {
                if (fid.startsWith(key) || fid.includes(key.replace('STAGE_', '').replace('FOH_', ''))) {
                    matchedData = settings[key];
                    break;
                }
            }

            if (matchedData) {
                const intensity = (matchedData.intensity !== undefined) ? matchedData.intensity : 0;
                let color = null;
                if (matchedData.color) color = new THREE.Color(matchedData.color);

                // Target Values for Smooth Transition
                mesh.userData.targetIntensity = intensity;
                if (color && mesh.userData.config.hasRGB) {
                    mesh.userData.targetColor.copy(color);
                } else if (!mesh.userData.config.hasRGB) {
                    // Non-RGB fixtures: scale intensity proportionally
                    mesh.userData.targetIntensity = intensity;
                }
            }
        });

        if (settings.SMOKE !== undefined) {
            this.toggleSmoke(settings.SMOKE);
        }
    }

    initScene() {
        this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: false, powerPreference: "low-power" });
        this.renderer.setSize(window.innerWidth - 320, window.innerHeight - 320); // Reduce width (sidebar) and height (console)
        this.renderer.setPixelRatio(1);
        this.renderer.shadowMap.enabled = false;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a2e);

        this.scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const dir = new THREE.DirectionalLight(0xffffff, 0.5);
        dir.position.set(5, 15, 10);
        this.scene.add(dir);

        this.camera = new THREE.PerspectiveCamera(50, (window.innerWidth - 320) / (window.innerHeight - 320), 0.1, 100);
        this.camera.position.set(0, 6, 22);

        this.controls = new OrbitControls(this.camera, this.canvas);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.1;
        this.controls.target.set(0, 2, 0);
        this.clock = new THREE.Clock();
    }

    initAssets() {
        const loader = new THREE.TextureLoader();
        this.textures = {
            woodStage: loader.load('./assets/textures/wood_stage.png', (t) => { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(4, 3); }),
            woodPanel: loader.load('./assets/textures/wood_panel.png', (t) => { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(2, 2); })
        };
    }

    buildArchitecture() {
        // ... (Same as before) ...
        const stageMat = new THREE.MeshLambertMaterial({ map: this.textures.woodStage });
        const stage = new THREE.Mesh(new THREE.BoxGeometry(CONFIG.stage.width, 1, CONFIG.stage.depth), stageMat);
        stage.position.set(0, 0.5, -CONFIG.stage.depth / 2);
        this.scene.add(stage);

        const floorMat = new THREE.MeshLambertMaterial({ color: 0x5a2d2d });
        const floor = new THREE.Mesh(new THREE.PlaneGeometry(CONFIG.auditorium.width, CONFIG.auditorium.depth), floorMat);
        floor.rotation.x = -Math.PI / 2; floor.position.set(0, 0, 10);
        this.scene.add(floor);

        const screenMat = new THREE.MeshLambertMaterial({ color: 0xffffff });
        const screen = new THREE.Mesh(new THREE.PlaneGeometry(9, 5), screenMat);
        screen.position.set(0, 4, -CONFIG.stage.depth + 0.2);
        this.scene.add(screen);

        const wingMat = new THREE.MeshLambertMaterial({ color: 0x0a2463, side: THREE.DoubleSide });
        for (let i = 0; i < 4; i++) {
            const z = -2 - (i * 2);
            const left = new THREE.Mesh(new THREE.PlaneGeometry(2, 6), wingMat);
            left.position.set(-7.5, 4, z); left.rotation.y = 0.4; this.scene.add(left);
            const right = new THREE.Mesh(new THREE.PlaneGeometry(2, 6), wingMat);
            right.position.set(7.5, 4, z); right.rotation.y = -0.4; this.scene.add(right);
        }

        const archMat = new THREE.MeshLambertMaterial({ map: this.textures.woodPanel });
        const leftPillar = new THREE.Mesh(new THREE.BoxGeometry(1.5, 7, 0.5), archMat);
        leftPillar.position.set(-8.5, 4.5, 0); this.scene.add(leftPillar);
        const rightPillar = new THREE.Mesh(new THREE.BoxGeometry(1.5, 7, 0.5), archMat);
        rightPillar.position.set(8.5, 4.5, 0); this.scene.add(rightPillar);
        const topArch = new THREE.Mesh(new THREE.BoxGeometry(19, 1.5, 0.5), archMat);
        topArch.position.set(0, 8.5, 0); this.scene.add(topArch);
    }

    createSmokeTexture() {
        const size = 128;
        const canvas = document.createElement('canvas');
        canvas.width = size; canvas.height = size;
        const ctx = canvas.getContext('2d');
        const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
        grad.addColorStop(0, 'rgba(200, 200, 200, 0.15)');
        grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, size, size);
        const texture = new THREE.CanvasTexture(canvas);
        return texture;
    }

    initSmoke() {
        if (this.smokeParticles) {
            this.scene.remove(this.smokeParticles);
            // dispose geometry/material logic ideally here
        }

        const particleCount = 150;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const velocities = [];

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 14;
            positions[i * 3 + 1] = Math.random() * 5 + 0.5;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 8 - 4;

            velocities.push({
                x: (Math.random() - 0.5) * 0.015,
                y: Math.random() * 0.01,
                z: (Math.random() - 0.5) * 0.015,
                phase: Math.random() * Math.PI * 2
            });
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const material = new THREE.PointsMaterial({
            size: 5,
            map: this.createSmokeTexture(),
            transparent: true,
            opacity: 0,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });

        this.smokeParticles = new THREE.Points(geometry, material);
        this.smokeParticles.userData.velocities = velocities;
        this.scene.add(this.smokeParticles);
    }

    updateSmoke(delta) {
        if (!this.smokeParticles) return;
        const positions = this.smokeParticles.geometry.attributes.position.array;
        const velocities = this.smokeParticles.userData.velocities;

        const targetOpacity = this.smokeActive ? 0.40 : 0;
        this.smokeParticles.material.opacity += (targetOpacity - this.smokeParticles.material.opacity) * delta * 0.5;

        if (this.smokeParticles.material.opacity > 0.01) {
            for (let i = 0; i < velocities.length; i++) {
                // Gentle swaying motion
                const vel = velocities[i];
                positions[i * 3] += vel.x + Math.sin(this.clock.elapsedTime * 0.5 + vel.phase) * 0.003;
                positions[i * 3 + 1] += vel.y;
                positions[i * 3 + 2] += vel.z + Math.cos(this.clock.elapsedTime * 0.3 + vel.phase) * 0.003;

                // Reset logic
                if (positions[i * 3 + 1] > 7 || Math.abs(positions[i * 3]) > 10) {
                    positions[i * 3] = (Math.random() - 0.5) * 14;
                    positions[i * 3 + 1] = 0.5;
                    positions[i * 3 + 2] = (Math.random() - 0.5) * 8 - 4;
                }
            }
            this.smokeParticles.geometry.attributes.position.needsUpdate = true;
        }
    }

    async initLightingRig() {
        const trussMat = new THREE.MeshLambertMaterial({ color: 0x111111 });
        const fohTruss = new THREE.Mesh(new THREE.BoxGeometry(18, 0.3, 0.3), trussMat);
        fohTruss.position.set(0, 7, 10); this.scene.add(fohTruss);
        [0, -2, -4, -6].forEach(z => {
            const pipe = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 16, 8), trussMat);
            pipe.rotation.z = Math.PI / 2; pipe.position.set(0, 8, z); this.scene.add(pipe);
        });

        try {
            const res = await fetch('./data/fixtures.json');
            const fixtureList = await res.json();
            this.fixtures = {};
            this.fixturesByGroup = {};
            console.log(`Loading ${fixtureList.length} fixtures...`);
            fixtureList.forEach(f => this.buildFixture(f));
        } catch (e) { console.error("Failed to load fixtures:", e); }
    }

    getFixtureConfig(fixtureType, fixtureId) {
        const type = fixtureType.toLowerCase();
        if (type.includes('smoke')) return { ...FIXTURE_DEFAULTS.smoke_machine };
        if (type.includes('blinder')) return { ...FIXTURE_DEFAULTS.blinder };
        if (type.includes('profile')) return { ...FIXTURE_DEFAULTS.profile };
        if (type.includes('fresnel')) return { ...FIXTURE_DEFAULTS.fresnel };
        if (type.includes('moving')) return { ...FIXTURE_DEFAULTS.moving_head };
        if (type.includes('par')) return fixtureId.toUpperCase().includes('RGB') ? { ...FIXTURE_DEFAULTS.par_rgb } : { ...FIXTURE_DEFAULTS.par };
        return { color: new THREE.Color(1, 0.95, 0.8), hasRGB: false };
    }

    buildFixture(f) {
        const config = this.getFixtureConfig(f.fixture_type, f.fixture_id);
        let mesh;
        const type = f.fixture_type.toLowerCase();

        if (type.includes('smoke')) mesh = Geometries.smoke_machine();
        else if (type.includes('profile')) mesh = Geometries.profile();
        else if (type.includes('fresnel')) mesh = Geometries.fresnel();
        else if (type.includes('blinder')) mesh = Geometries.blinder();
        else if (type.includes('moving')) mesh = Geometries.moving_head();
        else mesh = Geometries.par();

        const x = f.position.x; const y = f.position.z + 1.0; const z = f.position.y;
        mesh.position.set(x, y, z);
        let location = 'STAGE';
        if (z > 5) { location = 'FOH'; if (!config.isSmoke) mesh.lookAt(x, 1.5, 0); }
        else if (f.position.y < -6) { location = 'FLOOR'; mesh.position.y = 0.5; }
        else { if (!config.isSmoke) mesh.rotation.x = -Math.PI / 2; }
        this.scene.add(mesh);

        let light = null; let lens = null;
        if (!config.isSmoke) {
            light = new THREE.PointLight(config.color.clone(), 0, 20); light.position.set(0, -0.2, 0); mesh.add(light);
            const lensMat = new THREE.MeshBasicMaterial({ color: 0x111111 });
            lens = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 8), lensMat); lens.position.set(0, 0, 0.15); mesh.add(lens);
        }

        mesh.userData = {
            light, lens,
            fixtureId: f.fixture_id,
            fixtureType: f.fixture_type,
            groupId: f.group_id,
            location,
            config,
            intensity: 0,
            color: config.color ? config.color.clone() : new THREE.Color(0, 0, 0),
            targetIntensity: 0,
            targetColor: config.color ? config.color.clone() : new THREE.Color(0, 0, 0)
        };

        this.fixtures[f.fixture_id] = mesh;
    }

    toggleSmoke(on) { this.smokeActive = on; }

    onResize() {
        const height = window.innerHeight - 320;
        const width = window.innerWidth - 320;
        this.camera.aspect = width / height; this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        const delta = this.clock.getDelta();

        // Fetch the parsed transition configurations
        const dur = this.currentTransitionDuration || 2.0;
        const type = this.currentTransitionType || 'fade';

        // Intensity fraction max allowed per second: 100% total / dur
        const speed = dur > 0.1 ? (1.0 / dur) : 10.0;

        Object.values(this.fixtures).forEach(mesh => {
            if (mesh.userData.config.isSmoke) return;

            const intensityDiff = mesh.userData.targetIntensity - mesh.userData.intensity;

            if (type === 'cut' || dur <= 0.1) {
                // Instant snap
                mesh.userData.intensity = mesh.userData.targetIntensity;
            } else if (Math.abs(intensityDiff) > 0.1) {
                // Linear Transition over precise duration
                // We multiply speed by 100 because intensity is from 0-100.
                const step = (100.0 * speed) * delta;
                mesh.userData.intensity += Math.sign(intensityDiff) * Math.min(Math.abs(intensityDiff), step);
            } else {
                mesh.userData.intensity = mesh.userData.targetIntensity;
            }

            if (mesh.userData.config.hasRGB) {
                if (type === 'cut' || dur <= 0.1) {
                    mesh.userData.color.copy(mesh.userData.targetColor);
                } else {
                    const rDiff = mesh.userData.targetColor.r - mesh.userData.color.r;
                    const gDiff = mesh.userData.targetColor.g - mesh.userData.color.g;
                    const bDiff = mesh.userData.targetColor.b - mesh.userData.color.b;

                    // Colors are 0.0-1.0, so speed factor is straight speed * delta
                    const stepC = speed * delta;
                    mesh.userData.color.r += Math.sign(rDiff) * Math.min(Math.abs(rDiff), stepC);
                    mesh.userData.color.g += Math.sign(gDiff) * Math.min(Math.abs(gDiff), stepC);
                    mesh.userData.color.b += Math.sign(bDiff) * Math.min(Math.abs(bDiff), stepC);
                }
            }
            if (mesh.userData.light) {
                mesh.userData.light.intensity = mesh.userData.intensity;
                mesh.userData.light.color.copy(mesh.userData.color);
            }
            if (mesh.userData.lens) {
                if (mesh.userData.intensity > 1) {
                    if (mesh.userData.config.hasRGB) mesh.userData.lens.material.color.copy(mesh.userData.color);
                    else mesh.userData.lens.material.color.copy(mesh.userData.config.color);
                } else {
                    mesh.userData.lens.material.color.setHex(0x111111);
                }
            }
        });

        // Update UI every few frames or just every frame (simple)
        this.updateFixtureStatusUI();

        // Teleprompter: use server-sent elapsed, with client-side interpolation between updates
        if (this.latestState && !this.latestState.is_holding) {
            if (typeof this.latestState._cue_elapsed !== 'number') this.latestState._cue_elapsed = 0;
            this.latestState._cue_elapsed += delta;  // Smooth interpolation between server ticks
            this.updateTeleprompter(this.latestState);
        }

        this.updateSmoke(delta);
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}

new AuditoriumSimulation();
