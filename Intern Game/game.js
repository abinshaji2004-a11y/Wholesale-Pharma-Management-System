/**
 * Hill Climb Car Game - Main Game Module
 * State management, rendering loop, particles, items generation, input handling, and upgrades store.
 */

// Game constants
const CANVAS_WIDTH = 1024;
const CANVAS_HEIGHT = 576;
const PHYSICS_DT = 1 / 60;
const PHYSICS_SUBSTEPS = 8; // high substepping ensures physics stability

// Cost arrays
const UPGRADE_COSTS = [0, 150, 300, 500, 800, 1200, 1700, 2400, 3300, 4500]; // levels 1 to 10
const STAGE_UNLOCK_COSTS = {
    hills: 0,
    desert: 250,
    moon: 600
};

// Default State
const DEFAULT_STATE = {
    coins: 0,
    upgrades: {
        engine: 1,
        suspension: 1,
        tires: 1,
        fuel: 1
    },
    unlockedStages: {
        hills: true,
        desert: false,
        moon: false
    },
    records: {
        hills: 0,
        desert: 0,
        moon: 0
    }
};

class GameController {
    constructor() {
        // Game state
        this.state = 'LOBBY'; // LOBBY, PLAYING, PAUSED, CRASHED, OUT_OF_FUEL
        this.saveState = JSON.parse(JSON.stringify(DEFAULT_STATE));
        
        // Active stage selection
        this.selectedStage = 'hills';
        
        // Physics objects
        this.terrain = new Terrain('hills');
        this.car = new Car(100, 0); // start at x=100, y=height of terrain
        
        // Canvas rendering
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Camera
        this.camera = {
            x: 0,
            y: 0,
            scale: 1.0
        };
        
        // Input tracking
        this.keys = {};
        this.pedalGasActive = false;
        this.pedalBrakeActive = false;

        // Items and obstacles
        this.coins = [];
        this.fuels = [];
        this.particles = [];
        this.textPopups = [];
        this.maxGeneratedX = 0;
        
        // Scoring/Stats for current run
        this.currentDistance = 0;
        this.coinsCollectedThisRun = 0;
        
        // Engine RPM display
        this.currentRPM = 1000;
        this.targetRPM = 1000;
        
        // Timers and Animation Frame
        this.lastTime = 0;
        this.accumulator = 0;
        this.runDistanceRecordUpdated = false;

        // Initialize everything
        this.loadGame();
        this.initCanvas();
        this.initUI();
        this.bindEvents();
        this.resetGameRun();
        
        // Start rendering lobby loop
        requestAnimationFrame((t) => this.loop(t));
    }

    // Load from localstorage
    loadGame() {
        const data = localStorage.getItem('neon_climb_racing_save');
        if (data) {
            try {
                const parsed = JSON.parse(data);
                // Deep merge/fallback to handle version updates
                this.saveState.coins = parsed.coins ?? 0;
                this.saveState.upgrades = { ...DEFAULT_STATE.upgrades, ...parsed.upgrades };
                this.saveState.unlockedStages = { ...DEFAULT_STATE.unlockedStages, ...parsed.unlockedStages };
                this.saveState.records = { ...DEFAULT_STATE.records, ...parsed.records };
            } catch (e) {
                console.error("Failed to parse save state, resetting", e);
                this.saveState = JSON.parse(JSON.stringify(DEFAULT_STATE));
            }
        }
    }

    // Save to localstorage
    saveGame() {
        localStorage.setItem('neon_climb_racing_save', JSON.stringify(this.saveState));
    }

    initCanvas() {
        this.canvas.width = CANVAS_WIDTH;
        this.canvas.height = CANVAS_HEIGHT;
    }

    initUI() {
        this.updateLobbyUI();
        this.generateUpgradeBars();
    }

    updateLobbyUI() {
        document.getElementById('lobby-coins-val').innerText = this.saveState.coins;
        
        // Update stage records
        document.getElementById('record-hills').innerText = Math.round(this.saveState.records.hills) + 'm';
        document.getElementById('record-desert').innerText = Math.round(this.saveState.records.desert) + 'm';
        document.getElementById('record-moon').innerText = Math.round(this.saveState.records.moon) + 'm';

        // Update stage locks/selection
        ['hills', 'desert', 'moon'].forEach(stage => {
            const card = document.getElementById(`stage-${stage}`);
            const lock = document.getElementById(`lock-${stage}`);
            
            // Check selection
            if (this.selectedStage === stage) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }

            // Check lock state
            if (stage !== 'hills') {
                if (this.saveState.unlockedStages[stage]) {
                    lock.classList.add('hidden');
                } else {
                    lock.classList.remove('hidden');
                    // Setup unlock button cost
                    const unlockBtn = document.getElementById(`btn-unlock-${stage}`);
                    const cost = STAGE_UNLOCK_COSTS[stage];
                    if (this.saveState.coins < cost) {
                        unlockBtn.classList.add('cant-afford');
                    } else {
                        unlockBtn.classList.remove('cant-afford');
                    }
                }
            }
        });
    }

    generateUpgradeBars() {
        const parts = ['engine', 'suspension', 'tires', 'fuel'];
        
        parts.forEach(part => {
            const container = document.getElementById(`levels-${part}`);
            const currentLevel = this.saveState.upgrades[part];
            
            // Generate 10 bars
            container.innerHTML = '';
            for (let i = 1; i <= 10; i++) {
                const bar = document.createElement('div');
                bar.classList.add('level-bar');
                if (i <= currentLevel) {
                    bar.classList.add('filled');
                }
                container.appendChild(bar);
            }

            // Action row info
            const levelLabel = document.getElementById(`lbl-level-${part}`);
            const costLabel = document.getElementById(`cost-${part}`);
            const upgradeBtn = document.getElementById(`btn-upgrade-${part}`);

            if (currentLevel >= 10) {
                levelLabel.innerText = 'Lvl Max';
                upgradeBtn.className = 'upgrade-btn maxed';
                upgradeBtn.innerHTML = 'MAX';
            } else {
                levelLabel.innerText = `Lvl ${currentLevel}/10`;
                const cost = UPGRADE_COSTS[currentLevel]; // Cost for next level
                costLabel.innerText = cost;
                
                if (this.saveState.coins < cost) {
                    upgradeBtn.className = 'upgrade-btn disabled';
                } else {
                    upgradeBtn.className = 'upgrade-btn';
                }
            }
        });
    }

    bindEvents() {
        // Keyboard input
        window.addEventListener('keydown', (e) => {
            this.keys[e.key] = true;
            this.keys[e.code] = true;
            
            // Space to Pause/Resume during play
            if (e.key === ' ' || e.code === 'Space') {
                if (this.state === 'PLAYING') {
                    this.pauseGame();
                } else if (this.state === 'PAUSED') {
                    this.resumeGame();
                }
                e.preventDefault();
            }
        });

        window.addEventListener('keyup', (e) => {
            this.keys[e.key] = false;
            this.keys[e.code] = false;
        });

        // Stage click handlers
        ['hills', 'desert', 'moon'].forEach(stage => {
            const card = document.getElementById(`stage-${stage}`);
            card.addEventListener('click', (e) => {
                // If clicked unlock button, handle separately
                if (e.target.closest('.unlock-btn')) return;
                
                if (this.saveState.unlockedStages[stage]) {
                    this.selectedStage = stage;
                    window.gameAudio.playClick();
                    this.updateLobbyUI();
                }
            });
        });

        // Stage Unlock Buttons
        document.getElementById('btn-unlock-desert').addEventListener('click', () => this.unlockStage('desert', STAGE_UNLOCK_COSTS.desert));
        document.getElementById('btn-unlock-moon').addEventListener('click', () => this.unlockStage('moon', STAGE_UNLOCK_COSTS.moon));

        // Upgrade Buttons
        document.getElementById('btn-upgrade-engine').addEventListener('click', () => this.buyUpgrade('engine'));
        document.getElementById('btn-upgrade-suspension').addEventListener('click', () => this.buyUpgrade('suspension'));
        document.getElementById('btn-upgrade-tires').addEventListener('click', () => this.buyUpgrade('tires'));
        document.getElementById('btn-upgrade-fuel').addEventListener('click', () => this.buyUpgrade('fuel'));

        // Play Button
        document.getElementById('btn-start-game').addEventListener('click', () => this.startGame());

        // Audio controls
        const muteBtns = [document.getElementById('lobby-mute-btn'), document.getElementById('hud-mute-btn')];
        muteBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const isMuted = window.gameAudio.toggleMute();
                const icon = isMuted ? 
                    `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                        <line x1="23" y1="9" x2="17" y2="15"></line>
                        <line x1="17" y1="9" x2="23" y2="15"></line>
                     </svg>` : 
                    `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                        <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                     </svg>`;
                muteBtns.forEach(b => b.innerHTML = icon);
                window.gameAudio.playClick();
            });
        });

        // Pause HUD button
        document.getElementById('hud-pause-btn').addEventListener('click', () => {
            this.pauseGame();
        });

        // Popup buttons
        document.getElementById('btn-pause-resume').addEventListener('click', () => this.resumeGame());
        document.getElementById('btn-pause-lobby').addEventListener('click', () => this.returnToLobby());
        
        document.getElementById('btn-crash-retry').addEventListener('click', () => this.retryGame());
        document.getElementById('btn-crash-lobby').addEventListener('click', () => this.returnToLobby());
        
        document.getElementById('btn-fuel-retry').addEventListener('click', () => this.retryGame());
        document.getElementById('btn-fuel-lobby').addEventListener('click', () => this.returnToLobby());

        // Mobile Pedals Input Handlers
        const setupPedal = (elementId, type) => {
            const el = document.getElementById(elementId);
            const startPress = (e) => {
                e.preventDefault();
                el.classList.add('active');
                if (type === 'gas') this.pedalGasActive = true;
                if (type === 'brake') this.pedalBrakeActive = true;
                window.gameAudio.resumeContext(); // safe play audio context start
            };
            const stopPress = (e) => {
                e.preventDefault();
                el.classList.remove('active');
                if (type === 'gas') this.pedalGasActive = false;
                if (type === 'brake') this.pedalBrakeActive = false;
            };

            el.addEventListener('mousedown', startPress);
            el.addEventListener('mouseup', stopPress);
            el.addEventListener('mouseleave', stopPress);

            el.addEventListener('touchstart', startPress, {passive: false});
            el.addEventListener('touchend', stopPress, {passive: false});
            el.addEventListener('touchcancel', stopPress, {passive: false});
        };

        setupPedal('pedal-gas', 'gas');
        setupPedal('pedal-brake', 'brake');
    }

    unlockStage(stage, cost) {
        if (this.saveState.coins >= cost && !this.saveState.unlockedStages[stage]) {
            this.saveState.coins -= cost;
            this.saveState.unlockedStages[stage] = true;
            window.gameAudio.playUpgrade();
            this.saveGame();
            this.updateLobbyUI();
        }
    }

    buyUpgrade(part) {
        const currentLvl = this.saveState.upgrades[part];
        if (currentLvl < 10) {
            const cost = UPGRADE_COSTS[currentLvl];
            if (this.saveState.coins >= cost) {
                this.saveState.coins -= cost;
                this.saveState.upgrades[part]++;
                window.gameAudio.playUpgrade();
                this.saveGame();
                this.generateUpgradeBars();
                this.updateLobbyUI();
            }
        }
    }

    applyUpgradesToCar() {
        const engineLvl = this.saveState.upgrades.engine;
        const suspLvl = this.saveState.upgrades.suspension;
        const tiresLvl = this.saveState.upgrades.tires;
        const fuelLvl = this.saveState.upgrades.fuel;

        // Apply engine: 2400 at lvl 1, 4830 at lvl 10
        this.car.enginePower = 2400 + (engineLvl - 1) * 270;
        this.car.maxSpeed = 900 + (engineLvl - 1) * 50;

        // Apply suspension: Spring constants, rest length stays 46
        // Stiffness goes 3500 to 6200, damping goes 850 to 1390
        this.car.suspensionRestLength = 46;
        this.car.suspensionSpringK = 3500 + (suspLvl - 1) * 300;
        this.car.suspensionDampingC = 850 + (suspLvl - 1) * 60;

        // Apply tires: Grip multiplier from 1.15 to 1.87
        const gripFactor = 1.15 + (tiresLvl - 1) * 0.08;
        this.car.backWheel.grip = gripFactor;
        this.car.frontWheel.grip = gripFactor;

        // Apply fuel tank capacity: capacity 100 to 180, reduce burn rate slightly
        this.car.maxFuel = 100 + (fuelLvl - 1) * 15;
        this.car.fuelBurnRate = 4.2 - (fuelLvl - 1) * 0.12;

        // Sync initial values
        this.car.fuel = this.car.maxFuel;
    }

    startGame() {
        window.gameAudio.playClick();
        window.gameAudio.startEngine();
        
        this.state = 'PLAYING';
        
        // Hide lobby overlay, show HUD
        document.getElementById('lobby-screen').classList.add('hidden');
        document.getElementById('hud-overlay').style.display = 'flex';
        
        // Set terrain
        this.terrain.configureType(this.selectedStage);
        
        // Setup car physics parameters according to upgrade state
        this.applyUpgradesToCar();
        
        // Reset gameplay stats
        this.resetGameRun();
    }

    resetGameRun() {
        this.currentDistance = 0;
        this.coinsCollectedThisRun = 0;
        this.maxGeneratedX = 0;
        this.runDistanceRecordUpdated = false;

        this.coins = [];
        this.fuels = [];
        this.particles = [];
        this.textPopups = [];

        // Spawn car safely on the ground at x = 120 (aligned with suspension rest height 46 + wheel radius 22 + offset 12)
        const groundHeight = this.terrain.getHeight(120);
        this.car.pos.set(120, groundHeight + 80);
        this.car.vel.set(0, 0);
        this.car.angle = 0;
        this.car.angularVelocity = 0;
        this.car.resetWheels();
        
        // Center camera immediately
        this.camera.x = this.car.pos.x - 200;
        this.camera.y = this.car.pos.y - 50;
        this.camera.scale = 1.0;

        // Hide overlays
        document.getElementById('crashed-popup').classList.add('hidden');
        document.getElementById('fuel-popup').classList.add('hidden');
        document.getElementById('pause-popup').classList.add('hidden');

        // Populate initial terrain items
        this.generateItems(0, 1500);
    }

    retryGame() {
        window.gameAudio.playClick();
        window.gameAudio.startEngine();
        this.state = 'PLAYING';
        this.resetGameRun();
    }

    pauseGame() {
        if (this.state !== 'PLAYING') return;
        this.state = 'PAUSED';
        window.gameAudio.stopEngine();
        document.getElementById('pause-popup').classList.remove('hidden');
    }

    resumeGame() {
        if (this.state !== 'PAUSED') return;
        window.gameAudio.playClick();
        window.gameAudio.startEngine();
        this.state = 'PLAYING';
        document.getElementById('pause-popup').classList.add('hidden');
    }

    returnToLobby() {
        window.gameAudio.playClick();
        window.gameAudio.stopEngine();
        
        this.state = 'LOBBY';
        
        // Hide overlays and HUD, show lobby
        document.getElementById('crashed-popup').classList.add('hidden');
        document.getElementById('fuel-popup').classList.add('hidden');
        document.getElementById('pause-popup').classList.add('hidden');
        document.getElementById('hud-overlay').style.display = 'none';
        document.getElementById('lobby-screen').classList.remove('hidden');
        
        this.updateLobbyUI();
        this.generateUpgradeBars();
    }

    handleGameOver(reason) {
        this.state = reason; // CRASHED or OUT_OF_FUEL
        window.gameAudio.stopEngine();
        
        if (reason === 'CRASHED') {
            window.gameAudio.playCrash();
            // Wait 0.8 seconds before displaying popup for crash drama
            setTimeout(() => {
                if (this.state === 'CRASHED') {
                    this.showGameOverPopup('crashed-popup');
                }
            }, 800);
        } else {
            this.showGameOverPopup('fuel-popup');
        }
    }

    showGameOverPopup(popupId) {
        // Add collected coins to total wallet
        this.saveState.coins += this.coinsCollectedThisRun;
        
        // Check records
        let currentRecord = this.saveState.records[this.selectedStage] || 0;
        if (this.currentDistance > currentRecord) {
            this.saveState.records[this.selectedStage] = this.currentDistance;
            this.runDistanceRecordUpdated = true;
        }

        this.saveGame();

        // Update popup stats text
        const suffix = popupId === 'crashed-popup' ? 'crash' : 'fuel';
        document.getElementById(`${suffix}-dist-val`).innerText = Math.round(this.currentDistance) + 'm';
        document.getElementById(`${suffix}-coins-val`).innerText = '+' + this.coinsCollectedThisRun;
        document.getElementById(`${suffix}-best-val`).innerText = Math.round(this.saveState.records[this.selectedStage]) + 'm' + (this.runDistanceRecordUpdated ? ' (NEW RECORD!)' : '');

        document.getElementById(popupId).classList.remove('hidden');
    }

    // Procedural Coins and Fuel Generation
    generateItems(startX, endX) {
        // Prevent overlapping generations
        if (endX <= this.maxGeneratedX) return;
        
        let currentX = Math.max(startX, this.maxGeneratedX);
        
        while (currentX < endX) {
            // Check if we should spawn fuel: roughly every 1500 to 2200 pixels
            // Make sure the fuel is not too close to the start Flat zone
            if (currentX > 300 && Math.random() < 0.15 && (this.fuels.length === 0 || currentX - this.fuels[this.fuels.length - 1].x > 1400)) {
                const fuelX = currentX + 200 + Math.random() * 300;
                const fuelY = this.terrain.getHeight(fuelX) + 20;
                this.fuels.push({ x: fuelX, y: fuelY, radius: 18, active: true });
                currentX = fuelX + 100;
            } 
            // Spawn coin clusters: sequences of 3-5 coins
            else if (Math.random() < 0.3) {
                const count = 3 + Math.floor(Math.random() * 3); // 3 to 5 coins
                const spacing = 45;
                const clusterX = currentX + 150 + Math.random() * 200;
                const shape = Math.random() < 0.5 ? 'arc' : 'terrain'; // either curved arc or trace ground
                
                const peakHeight = 40 + Math.random() * 40;
                for (let i = 0; i < count; i++) {
                    const cx = clusterX + i * spacing;
                    let cy = this.terrain.getHeight(cx) + 22;
                    if (shape === 'arc') {
                        cy += Math.sin((i / (count - 1)) * Math.PI) * peakHeight;
                    }
                    this.coins.push({ x: cx, y: cy, radius: 11, active: true });
                }
                currentX = clusterX + count * spacing + 100;
            } else {
                currentX += 200;
            }
        }
        
        this.maxGeneratedX = endX;
    }

    // MAIN GAME LOOP (Handles frame intervals, updates, and rendering)
    loop(timestamp) {
        if (!this.lastTime) this.lastTime = timestamp;
        let dt = (timestamp - this.lastTime) / 1000;
        this.lastTime = timestamp;
        
        // Prevent huge frame step on background tabs
        if (dt > 0.1) dt = 0.1;

        if (this.state === 'PLAYING') {
            this.accumulator += dt;
            
            // Physics updates with fixed delta time sub-stepping
            while (this.accumulator >= PHYSICS_DT) {
                // Perform substepping for extremely smooth and stable springs
                const subDT = PHYSICS_DT / PHYSICS_SUBSTEPS;
                for (let step = 0; step < PHYSICS_SUBSTEPS; step++) {
                    this.updatePhysics(subDT);
                }
                this.accumulator -= PHYSICS_DT;
            }
            
            // Trigger procedural generation ahead of car
            const genHorizon = this.car.pos.x + 1500;
            if (genHorizon > this.maxGeneratedX) {
                this.generateItems(this.maxGeneratedX, genHorizon);
            }
        }

        // Camera smoothly follows car
        this.updateCamera(dt);
        
        // Render scene
        this.render();

        requestAnimationFrame((t) => this.loop(t));
    }

    updatePhysics(dt) {
        // Collect user controls
        let gasInput = 0;
        let brakeInput = 0;
        
        if (this.keys['ArrowRight'] || this.keys['KeyD'] || this.pedalGasActive) {
            gasInput = 1.0;
        }
        if (this.keys['ArrowLeft'] || this.keys['KeyA'] || this.pedalBrakeActive) {
            brakeInput = 1.0;
        }

        this.car.controls.gas = gasInput;
        this.car.controls.brake = brakeInput;
        this.car.controls.tiltLeft = this.keys['KeyQ'] || this.keys['ArrowUp'];
        this.car.controls.tiltRight = this.keys['KeyE'] || this.keys['ArrowDown'];

        // Perform main physics update
        this.car.update(dt, this.terrain);

        // Update current run distance (scale meters: 1 meter = 100 pixels)
        const meters = this.car.pos.x / 100;
        if (meters > this.currentDistance) {
            this.currentDistance = meters;
        }

        // Check gameplay triggers (crash & out of fuel)
        if (this.car.isCrashed) {
            this.handleGameOver('CRASHED');
            return;
        }
        if (this.car.fuel <= 0 && this.car.vel.length() < 10 && !this.car.backWheel.onGround && !this.car.frontWheel.onGround) {
            // Allow rolling to a stop, but if stopped and zero fuel, trigger Game Over
            this.handleGameOver('OUT_OF_FUEL');
            return;
        }
        if (this.car.fuel <= 0 && this.car.vel.length() < 12 && (this.car.backWheel.onGround || this.car.frontWheel.onGround)) {
             this.handleGameOver('OUT_OF_FUEL');
             return;
        }

        // Check item collisions
        const carBoxRadius = 35;
        
        // Collision with coins
        this.coins.forEach(coin => {
            if (!coin.active) return;
            // Check chassis collision or wheel collision
            const distChassis = this.car.pos.sub(new Vector2D(coin.x, coin.y)).length();
            const distWheelBack = this.car.backWheel.pos.sub(new Vector2D(coin.x, coin.y)).length();
            const distWheelFront = this.car.frontWheel.pos.sub(new Vector2D(coin.x, coin.y)).length();

            if (distChassis < carBoxRadius + coin.radius || 
                distWheelBack < this.car.backWheel.radius + coin.radius || 
                distWheelFront < this.car.frontWheel.radius + coin.radius) {
                
                coin.active = false;
                this.coinsCollectedThisRun += 10;
                window.gameAudio.playCoin();
                
                // Add text popup
                this.textPopups.push({
                    x: coin.x,
                    y: coin.y + 15,
                    text: "+10",
                    color: "#2cb67d",
                    opacity: 1,
                    velY: 60
                });

                // Spawn sparkles
                for (let i = 0; i < 6; i++) {
                    this.particles.push({
                        x: coin.x,
                        y: coin.y,
                        vx: (Math.random() - 0.5) * 120,
                        vy: (Math.random() - 0.5) * 120 + 40,
                        color: '#ffd700',
                        size: 3 + Math.random() * 3,
                        alpha: 1.0,
                        life: 0.4 + Math.random() * 0.3
                    });
                }
            }
        });

        // Collision with fuel canisters
        this.fuels.forEach(fuel => {
            if (!fuel.active) return;
            const distChassis = this.car.pos.sub(new Vector2D(fuel.x, fuel.y)).length();
            const distWheelBack = this.car.backWheel.pos.sub(new Vector2D(fuel.x, fuel.y)).length();
            const distWheelFront = this.car.frontWheel.pos.sub(new Vector2D(fuel.x, fuel.y)).length();

            if (distChassis < carBoxRadius + fuel.radius || 
                distWheelBack < this.car.backWheel.radius + fuel.radius || 
                distWheelFront < this.car.frontWheel.radius + fuel.radius) {
                
                fuel.active = false;
                
                // Refill fuel
                this.car.fuel = Math.min(this.car.maxFuel, this.car.fuel + this.car.maxFuel * 0.45); // 45% refill
                window.gameAudio.playFuel();

                this.textPopups.push({
                    x: fuel.x,
                    y: fuel.y + 20,
                    text: "FUEL REFILL!",
                    color: "#00d2ff",
                    opacity: 1,
                    velY: 80
                });

                // Spawn bubble gas particles
                for (let i = 0; i < 10; i++) {
                    this.particles.push({
                        x: fuel.x,
                        y: fuel.y,
                        vx: (Math.random() - 0.5) * 90,
                        vy: Math.random() * 120 + 20,
                        color: '#ff4b4b',
                        size: 4 + Math.random() * 5,
                        alpha: 1.0,
                        life: 0.6 + Math.random() * 0.4
                    });
                }
            }
        });

        // Spawn tyre particles (dust) when wheels spin on ground
        [this.car.backWheel, this.car.frontWheel].forEach((wheel, idx) => {
            if (wheel.onGround && Math.abs(wheel.angularVelocity) > 2) {
                const contactPoint = wheel.pos.sub(wheel.groundNormal.mult(wheel.radius));
                
                // Base spawning probability
                let spawnProb = 0.12;
                if (this.car.controls.gas > 0) spawnProb = 0.45;
                
                if (Math.random() < spawnProb) {
                    const dustColor = this.selectedStage === 'desert' ? '#ff9b42' : 
                                      this.selectedStage === 'moon' ? '#cfd2d6' : '#738a53';
                    
                    this.particles.push({
                        x: contactPoint.x,
                        y: contactPoint.y,
                        vx: -wheel.angularVelocity * wheel.radius * 0.2 + (Math.random() - 0.5) * 40,
                        vy: Math.random() * 60 + 10,
                        color: dustColor,
                        size: 2 + Math.random() * 4,
                        alpha: 0.6,
                        life: 0.3 + Math.random() * 0.4
                    });
                }
            }
        });

        // Exhaust smoke from exhaust pipe
        if (Math.random() < 0.25) {
            // Local exhaust offset relative to chassis
            const localExhaust = new Vector2D(-55, -4);
            const exhaustWorld = this.car.pos.add(localExhaust.rotate(this.car.angle));
            
            // Speed of smoke depends on gas pedal
            const smokeVel = new Vector2D(-80 - this.car.controls.gas * 100, (Math.random() - 0.5) * 30).rotate(this.car.angle);
            
            this.particles.push({
                x: exhaustWorld.x,
                y: exhaustWorld.y,
                vx: smokeVel.x + this.car.vel.x * 0.4,
                vy: smokeVel.y + this.car.vel.y * 0.4,
                color: this.car.controls.gas > 0 ? 'rgba(150, 150, 160, 0.4)' : 'rgba(210, 210, 220, 0.25)',
                size: 3 + Math.random() * 4,
                alpha: 0.7,
                life: 0.4 + Math.random() * 0.4
            });
        }

        // Update active particles
        this.particles.forEach(p => {
            p.x += p.vx * dt;
            p.y += p.vy * dt;
            p.life -= dt;
            p.alpha = Math.max(0, p.life * 1.5);
        });
        this.particles = this.particles.filter(p => p.life > 0);

        // Update text popups
        this.textPopups.forEach(tp => {
            tp.y += tp.velY * dt;
            tp.opacity -= dt * 1.5;
        });
        this.textPopups = this.textPopups.filter(tp => tp.opacity > 0);

        // Calculate and smooth engine RPM audio & dashboard meter
        if (this.car.fuel > 0) {
            const absWheelSpeed = Math.abs(this.car.backWheel.angularVelocity) * this.car.backWheel.radius;
            const speedRatio = absWheelSpeed / this.car.maxSpeed;

            if (this.car.backWheel.onGround || this.car.frontWheel.onGround) {
                // Engine RPM locked to wheel speed, plus a boost for throttle
                this.targetRPM = 1000 + (speedRatio * 5500) + (this.car.controls.gas * 1200);
            } else {
                // In air, engine revs up quickly when gas is pinned
                if (this.car.controls.gas > 0) {
                    this.targetRPM = Math.min(8000, this.targetRPM + dt * 25000);
                } else {
                    this.targetRPM = Math.max(1000, this.targetRPM - dt * 15000);
                }
            }
        } else {
            // Dead engine RPM drops to 0
            this.targetRPM = Math.max(0, this.targetRPM - dt * 8000);
        }

        this.currentRPM += (this.targetRPM - this.currentRPM) * 0.15;
        this.currentRPM = Math.max(0, Math.min(8000, this.currentRPM));

        const rpmRatio = this.currentRPM / 8000;
        window.gameAudio.updateEngine(rpmRatio, this.car.controls.gas);

        // Update HUD HTML components
        this.updateHUDText();
    }

    updateCamera(dt) {
        // Base target position: follow car, centered left at 30% width
        const targetCamX = this.car.pos.x - 280;
        const targetCamY = this.car.pos.y - 40;

        // Camera lag/smoothing
        this.camera.x += (targetCamX - this.camera.x) * 0.08;
        this.camera.y += (targetCamY - this.camera.y) * 0.08;

        // Prevent camera from showing left of start flat boundary
        if (this.camera.x < -80) this.camera.x = -80;

        // Dynamic scale zoom based on speed: zooms out when fast
        const speed = this.car.vel.length();
        const targetScale = 1.05 - Math.min(0.3, speed / (this.car.maxSpeed * 1.3));
        this.camera.scale += (targetScale - this.camera.scale) * 0.05;
    }

    updateHUDText() {
        if (this.state !== 'PLAYING') return;

        document.getElementById('hud-dist-val').innerText = Math.round(this.currentDistance);
        document.getElementById('hud-coins-val').innerText = this.coinsCollectedThisRun;
        
        // Fuel Bar percentage
        const fuelPct = Math.round((this.car.fuel / this.car.maxFuel) * 100);
        document.getElementById('fuel-percent-lbl').innerText = fuelPct + '%';
        
        const fuelBar = document.getElementById('fuel-bar-fill');
        fuelBar.style.width = fuelPct + '%';

        // Warning alerts on low fuel (below 25%)
        const fuelCard = document.getElementById('hud-fuel-card');
        if (fuelPct < 25) {
            fuelCard.classList.add('fuel-warning');
        } else {
            fuelCard.classList.remove('fuel-warning');
        }

        // Speed Dial (mapped to horizontal velocity)
        const kmh = Math.round(Math.max(0, this.car.vel.x * 0.08)); // Scale factor for nice readouts
        document.getElementById('hud-speed-val').innerText = kmh;
        
        // Speed SVG Stroke offset
        const maxKmh = 140;
        const speedPct = Math.min(1.0, kmh / maxKmh);
        const circleLength = 251.2; // 2 * PI * Radius(40)
        // Dashoffset: 0 = full, 251.2 = empty
        document.getElementById('speed-dial-fill').style.strokeDashoffset = circleLength * (1 - speedPct);

        // RPM Dial
        const displayRPM = Math.round(this.currentRPM / 100);
        document.getElementById('hud-rpm-val').innerText = displayRPM;
        
        const rpmPct = this.currentRPM / 8000;
        document.getElementById('rpm-dial-fill').style.strokeDashoffset = circleLength * (1 - rpmPct);
    }

    // SCENE RENDERING
    render() {
        // Clear screen
        this.ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Draw Parallax Sky Background
        this.drawBackground();

        // Draw parallax midground details (moves slower than camera)
        this.drawParallaxHills();

        // Draw active items (Coins & Fuel)
        this.drawItems();

        // Draw dust and smoke particles
        this.drawParticles();

        // Draw terrain line
        this.drawTerrain();

        // Draw car chassis, wheels, driver
        this.drawCar();

        // Draw Floating Text Popups (+10 etc)
        this.drawTextPopups();
    }

    drawBackground() {
        const grad = this.ctx.createLinearGradient(0, 0, 0, CANVAS_HEIGHT);
        
        if (this.selectedStage === 'desert') {
            // Sunset Desert vibe
            grad.addColorStop(0, '#1a0b2e'); // Deep violet sky
            grad.addColorStop(0.5, '#7b2c5d'); // Crimson pink
            grad.addColorStop(1, '#df5e3a'); // Sandy orange horizon
            this.ctx.fillStyle = grad;
            this.ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
            
            // Draw a huge glowing sun
            this.ctx.beginPath();
            this.ctx.arc(CANVAS_WIDTH * 0.7, CANVAS_HEIGHT * 0.45, 60, 0, Math.PI * 2);
            this.ctx.fillStyle = 'rgba(255, 140, 60, 0.4)';
            this.ctx.shadowColor = '#ff5e62';
            this.ctx.shadowBlur = 40;
            this.ctx.fill();
            this.ctx.shadowBlur = 0; // reset glow
        } else if (this.selectedStage === 'moon') {
            // Space/Lunar theme
            grad.addColorStop(0, '#020005');
            grad.addColorStop(0.7, '#070512');
            grad.addColorStop(1, '#0e0b25');
            this.ctx.fillStyle = grad;
            this.ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

            // Draw small stars
            this.ctx.fillStyle = '#ffffff';
            const starSeeds = [
                {x: 120, y: 80, r: 1}, {x: 350, y: 150, r: 1.5}, {x: 820, y: 70, r: 1},
                {x: 650, y: 220, r: 1.2}, {x: 940, y: 180, r: 1}, {x: 230, y: 310, r: 0.8},
                {x: 50, y: 240, r: 1.3}, {x: 520, y: 90, r: 1.5}, {x: 740, y: 340, r: 0.8}
            ];
            starSeeds.forEach(star => {
                this.ctx.beginPath();
                this.ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
                this.ctx.fill();
            });

            // Draw a glowing planet Earth in background
            this.ctx.beginPath();
            this.ctx.arc(CANVAS_WIDTH * 0.25, CANVAS_HEIGHT * 0.35, 45, 0, Math.PI * 2);
            const earthGrad = this.ctx.createRadialGradient(
                CANVAS_WIDTH * 0.23, CANVAS_HEIGHT * 0.33, 5,
                CANVAS_WIDTH * 0.25, CANVAS_HEIGHT * 0.35, 45
            );
            earthGrad.addColorStop(0, '#00d2ff');
            earthGrad.addColorStop(0.7, '#0047b3');
            earthGrad.addColorStop(1, '#02000c');
            this.ctx.fillStyle = earthGrad;
            this.ctx.shadowColor = '#00d2ff';
            this.ctx.shadowBlur = 30;
            this.ctx.fill();
            this.ctx.shadowBlur = 0;
        } else {
            // Earth Green Hills Sky (Blue gradient to purple horizon)
            grad.addColorStop(0, '#070f24'); // night blue
            grad.addColorStop(0.6, '#0f2b5c');
            grad.addColorStop(1, '#341f5c'); // deep horizon
            this.ctx.fillStyle = grad;
            this.ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
            
            // Draw a soft glowing moon
            this.ctx.beginPath();
            this.ctx.arc(CANVAS_WIDTH * 0.8, CANVAS_HEIGHT * 0.28, 30, 0, Math.PI * 2);
            this.ctx.fillStyle = 'rgba(230, 240, 255, 0.55)';
            this.ctx.shadowColor = '#7f5af0';
            this.ctx.shadowBlur = 25;
            this.ctx.fill();
            this.ctx.shadowBlur = 0;
        }
    }

    drawParallaxHills() {
        const scale = this.camera.scale;
        const skyBaseY = CANVAS_HEIGHT * 0.65;
        const startX = -100;
        const endX = CANVAS_WIDTH + 100;
        const step = 60;
        
        // Deep Background mountains (moves at 0.15 relative to camera)
        this.ctx.save();
        this.ctx.fillStyle = this.selectedStage === 'desert' ? '#4d1a40' : 
                             this.selectedStage === 'moon' ? '#080516' : '#170e34';
        this.ctx.beginPath();
        
        // Calculate starting offset based on camera position
        const pOffset1 = -this.camera.x * 0.12 * scale;
        const pCamY1 = this.camera.y * 0.12 * scale;

        this.ctx.moveTo(startX, CANVAS_HEIGHT + 100);
        for (let sx = startX; sx <= endX; sx += step) {
            // Convert screen X to a world coordinate for the noise function
            const wx = (sx - CANVAS_WIDTH * 0.3) / scale + this.camera.x * 0.88;
            const wy = Math.cos(wx * 0.001) * 80 + Math.sin(wx * 0.004) * 20 - 60;
            
            const sy = skyBaseY - (wy - this.camera.y * 0.15) * scale;
            this.ctx.lineTo(sx, sy);
        }
        this.ctx.lineTo(endX, CANVAS_HEIGHT + 100);
        this.ctx.closePath();
        this.ctx.fill();
        this.ctx.restore();

        // Mid Background hills (moves at 0.35 relative to camera)
        this.ctx.save();
        this.ctx.fillStyle = this.selectedStage === 'desert' ? '#7b2c3a' : 
                             this.selectedStage === 'moon' ? '#110d21' : '#16234b';
        this.ctx.beginPath();

        this.ctx.moveTo(startX, CANVAS_HEIGHT + 100);
        for (let sx = startX; sx <= endX; sx += step) {
            const wx = (sx - CANVAS_WIDTH * 0.3) / scale + this.camera.x * 0.65;
            const wy = Math.sin(wx * 0.002) * 90 + Math.cos(wx * 0.007) * 25 - 120;
            
            const sy = skyBaseY - (wy - this.camera.y * 0.35) * scale;
            this.ctx.lineTo(sx, sy);
        }
        this.ctx.lineTo(endX, CANVAS_HEIGHT + 100);
        this.ctx.closePath();
        this.ctx.fill();
        this.ctx.restore();
    }

    drawTerrain() {
        const scale = this.camera.scale;
        const startX = -100;
        const endX = CANVAS_WIDTH + 100;
        const step = 6; // resolution

        // Fill color block below terrain
        const gradTerrain = this.ctx.createLinearGradient(0, CANVAS_HEIGHT, 0, 0);
        
        if (this.selectedStage === 'desert') {
            gradTerrain.addColorStop(0, '#421313'); // deep red bottom
            gradTerrain.addColorStop(0.6, '#963c1b'); // sandy core
            gradTerrain.addColorStop(1, '#d56024'); // orange sand top
        } else if (this.selectedStage === 'moon') {
            gradTerrain.addColorStop(0, '#0c0b16');
            gradTerrain.addColorStop(0.6, '#202230');
            gradTerrain.addColorStop(1, '#44495c');
        } else {
            gradTerrain.addColorStop(0, '#06140d'); // dark forest floor bottom
            gradTerrain.addColorStop(0.6, '#13381d'); // muddy core
            gradTerrain.addColorStop(1, '#246b2b'); // bright grass top
        }

        this.ctx.fillStyle = gradTerrain;
        this.ctx.beginPath();
        
        this.ctx.moveTo(startX, CANVAS_HEIGHT + 100);
        for (let sx = startX; sx <= endX; sx += step) {
            // Convert screen X to world X
            const wx = (sx - CANVAS_WIDTH * 0.3) / scale + this.camera.x;
            const wy = this.terrain.getHeight(wx);
            // Convert world Y to screen Y
            const sy = CANVAS_HEIGHT * 0.65 - (wy - this.camera.y) * scale;
            this.ctx.lineTo(sx, sy);
        }
        this.ctx.lineTo(endX, CANVAS_HEIGHT + 100);
        this.ctx.closePath();
        this.ctx.fill();

        // Draw top neon edge highlight
        this.ctx.strokeStyle = this.selectedStage === 'desert' ? '#ff9e00' : 
                               this.selectedStage === 'moon' ? '#00d2ff' : '#2cb67d';
        this.ctx.lineWidth = 3 * scale;
        
        // Optional glowing neon border
        this.ctx.shadowColor = this.ctx.strokeStyle;
        this.ctx.shadowBlur = 6;
        
        this.ctx.beginPath();
        let first = true;
        for (let sx = startX; sx <= endX; sx += step) {
            const wx = (sx - CANVAS_WIDTH * 0.3) / scale + this.camera.x;
            const wy = this.terrain.getHeight(wx);
            const sy = CANVAS_HEIGHT * 0.65 - (wy - this.camera.y) * scale;
            if (first) {
                this.ctx.moveTo(sx, sy);
                first = false;
            } else {
                this.ctx.lineTo(sx, sy);
            }
        }
        this.ctx.stroke();
        
        this.ctx.shadowBlur = 0; // reset blur
    }

    drawItems() {
        const scale = this.camera.scale;
        
        // Draw Coins
        this.coins.forEach(coin => {
            if (!coin.active) return;
            
            const screenX = (coin.x - this.camera.x) * scale + CANVAS_WIDTH * 0.3;
            const screenY = CANVAS_HEIGHT * 0.65 - (coin.y - this.camera.y) * scale;
            
            // Only draw if within screen bounds
            if (screenX < -20 || screenX > CANVAS_WIDTH + 20) return;

            const rScaled = coin.radius * scale;

            this.ctx.save();
            this.ctx.beginPath();
            this.ctx.arc(screenX, screenY, rScaled, 0, Math.PI * 2);
            
            // Coin gold radial gradient
            const coinGrad = this.ctx.createRadialGradient(
                screenX - 3 * scale, screenY - 3 * scale, 1 * scale,
                screenX, screenY, rScaled
            );
            coinGrad.addColorStop(0, '#fff69c');
            coinGrad.addColorStop(0.7, '#ffd700');
            coinGrad.addColorStop(1, '#cc9900');
            
            this.ctx.fillStyle = coinGrad;
            this.ctx.strokeStyle = '#fff';
            this.ctx.lineWidth = 1.2 * scale;
            
            this.ctx.shadowColor = '#ffd700';
            this.ctx.shadowBlur = 10;
            
            this.ctx.fill();
            this.ctx.stroke();
            
            // Draw inner dollar icon
            this.ctx.fillStyle = '#9e7300';
            this.ctx.font = 'bold ' + Math.round(11 * scale) + 'px ' + var_font_fallback();
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText('$', screenX, screenY + 0.5 * scale);

            this.ctx.restore();
        });

        // Draw Fuel Canisters
        this.fuels.forEach(fuel => {
            if (!fuel.active) return;
            
            const screenX = (fuel.x - this.camera.x) * scale + CANVAS_WIDTH * 0.3;
            const screenY = CANVAS_HEIGHT * 0.65 - (fuel.y - this.camera.y) * scale;
            
            if (screenX < -30 || screenX > CANVAS_WIDTH + 30) return;

            this.ctx.save();
            
            // Fuel Jerrycan drawing (styled as a red glowing drum canister)
            const w = 22 * scale;
            const h = 30 * scale;
            
            this.ctx.beginPath();
            this.ctx.rect(screenX - w/2, screenY - h/2, w, h);
            
            const fuelGrad = this.ctx.createLinearGradient(screenX - w/2, screenY, screenX + w/2, screenY);
            fuelGrad.addColorStop(0, '#ff4747');
            fuelGrad.addColorStop(0.5, '#ff8080');
            fuelGrad.addColorStop(1, '#bf1e1e');
            
            this.ctx.fillStyle = fuelGrad;
            this.ctx.strokeStyle = '#fff';
            this.ctx.lineWidth = 1.8 * scale;
            this.ctx.shadowColor = '#ff4b4b';
            this.ctx.shadowBlur = 12;
            
            this.ctx.fill();
            this.ctx.stroke();

            // Draw nozzle on top
            this.ctx.beginPath();
            this.ctx.rect(screenX - 7 * scale, screenY - h/2 - 4 * scale, 5 * scale, 4 * scale);
            this.ctx.fillStyle = '#ff8080';
            this.ctx.fill();

            // Draw handles
            this.ctx.beginPath();
            this.ctx.rect(screenX - 3 * scale, screenY - h/2 - 3 * scale, 7 * scale, 3 * scale);
            this.ctx.fillStyle = '#222';
            this.ctx.fill();

            // Draw "GAS" text inside
            this.ctx.fillStyle = '#fff';
            this.ctx.font = 'bold ' + Math.round(7 * scale) + 'px ' + var_font_fallback();
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText('GAS', screenX, screenY);

            this.ctx.restore();
        });
    }

    drawParticles() {
        const scale = this.camera.scale;
        this.particles.forEach(p => {
            const screenX = (p.x - this.camera.x) * scale + CANVAS_WIDTH * 0.3;
            const screenY = CANVAS_HEIGHT * 0.65 - (p.y - this.camera.y) * scale;
            
            if (screenX < -10 || screenX > CANVAS_WIDTH + 10) return;

            this.ctx.save();
            this.ctx.beginPath();
            this.ctx.arc(screenX, screenY, p.size * scale, 0, Math.PI * 2);
            this.ctx.fillStyle = p.color;
            this.ctx.globalAlpha = p.alpha;
            this.ctx.fill();
            this.ctx.restore();
        });
    }

    drawTextPopups() {
        const scale = this.camera.scale;
        this.textPopups.forEach(tp => {
            const screenX = (tp.x - this.camera.x) * scale + CANVAS_WIDTH * 0.3;
            const screenY = CANVAS_HEIGHT * 0.65 - (tp.y - this.camera.y) * scale;
            
            this.ctx.save();
            this.ctx.fillStyle = tp.color;
            this.ctx.globalAlpha = tp.opacity;
            this.ctx.font = 'bold ' + Math.round(14 * scale) + 'px ' + var_font_fallback();
            this.ctx.textAlign = 'center';
            this.ctx.fillText(tp.text, screenX, screenY);
            this.ctx.restore();
        });
    }

    drawCar() {
        const scale = this.camera.scale;
        const screenCarX = (this.car.pos.x - this.camera.x) * scale + CANVAS_WIDTH * 0.3;
        const screenCarY = CANVAS_HEIGHT * 0.65 - (this.car.pos.y - this.camera.y) * scale;

        this.ctx.save();
        
        // Translate, scale, and rotate to match Car Chassis
        // Note: we rotate by -angle because Canvas Y goes down while physics Y goes up!
        this.ctx.translate(screenCarX, screenCarY);
        this.ctx.scale(scale, scale);
        this.ctx.rotate(-this.car.angle);

        // 1. Draw Exhaust Pipe
        this.ctx.fillStyle = '#444';
        this.ctx.fillRect(-60, 0, 12, 6);

        // 2. Draw Main Chassis (Cyber Jeep style)
        const frameGrad = this.ctx.createLinearGradient(-50, 0, 50, 0);
        frameGrad.addColorStop(0, '#190a38');
        frameGrad.addColorStop(0.5, '#351570');
        frameGrad.addColorStop(1, '#5323a6');
        
        this.ctx.fillStyle = frameGrad;
        this.ctx.strokeStyle = '#c495ff';
        this.ctx.lineWidth = 3.5;
        this.ctx.shadowColor = '#9b5de5';
        this.ctx.shadowBlur = this.car.controls.gas > 0 ? 15 : 6;

        this.ctx.beginPath();
        // Drawing outline of the chassis (offset vertically by +12 to sit right relative to center)
        // Since Y goes DOWN in Canvas:
        // Chassis local coordinates in physics (where localOffset was relative to chassis center)
        // Wheels are at (-40, -12), and (40, -12).
        // Let's draw the body shifted slightly up relative to center so wheels look connected.
        this.ctx.moveTo(-55, 6);    // rear bottom
        this.ctx.lineTo(-55, -14);  // rear back flap
        this.ctx.lineTo(-20, -18);  // cabin back
        this.ctx.lineTo(2, -34);    // windshield start
        this.ctx.lineTo(25, -34);   // hood back
        this.ctx.lineTo(65, -14);   // front nose top (extended for wider wheelbase)
        this.ctx.lineTo(65, 4);     // front nose bottom
        this.ctx.lineTo(70, 4);     // front wheel arch front edge
        this.ctx.arc(46, 8, 24, 0, Math.PI, true); // front wheel arch
        this.ctx.lineTo(-22, 4);    // middle undercarriage
        this.ctx.arc(-46, 8, 24, 0, Math.PI, true); // back wheel arch
        this.ctx.closePath();
        this.ctx.fill();
        this.ctx.stroke();

        this.ctx.shadowBlur = 0; // reset blur

        // 3. Draw cabin canopy window (glass canopy)
        this.ctx.fillStyle = 'rgba(0, 210, 255, 0.3)';
        this.ctx.strokeStyle = '#00d2ff';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(-18, -18);
        this.ctx.lineTo(0, -32);
        this.ctx.lineTo(22, -32);
        this.ctx.lineTo(10, -18);
        this.ctx.closePath();
        this.ctx.fill();
        this.ctx.stroke();

        // 4. Draw driver inside the cockpit
        this.drawDriver();

        // 5. Headlight / Taillight glowing dots
        // Headlight (front right)
        this.ctx.beginPath();
        this.ctx.arc(53, -6, 4, 0, Math.PI*2);
        this.ctx.fillStyle = '#00ffff';
        this.ctx.shadowColor = '#00ffff';
        this.ctx.shadowBlur = 15;
        this.ctx.fill();
        
        // Headlight beam (cone)
        const beamGrad = this.ctx.createRadialGradient(53, -6, 2, 130, -12, 60);
        beamGrad.addColorStop(0, 'rgba(0, 255, 255, 0.45)');
        beamGrad.addColorStop(1, 'rgba(0, 255, 255, 0.0)');
        this.ctx.fillStyle = beamGrad;
        this.ctx.beginPath();
        this.ctx.moveTo(53, -6);
        this.ctx.lineTo(130, -25);
        this.ctx.lineTo(130, 5);
        this.ctx.closePath();
        this.ctx.fill();
        
        // Taillight (rear left)
        this.ctx.beginPath();
        this.ctx.arc(-54, -8, 3, 0, Math.PI*2);
        this.ctx.fillStyle = '#ff3333';
        this.ctx.shadowColor = '#ff3333';
        this.ctx.shadowBlur = 10;
        this.ctx.fill();
        
        this.ctx.shadowBlur = 0; // reset

        this.ctx.restore(); // restores from car chassis translations

        // 6. Draw Wheels (Draw in world coords because suspension lets them move independently)
        this.drawWheel(this.car.backWheel);
        this.drawWheel(this.car.frontWheel);
    }

    drawDriver() {
        // Driver head local position (0, 32) in physics.
        // In canvas (flipped Y): head is at (0, -32) relative to chassis center.
        const bounce = Math.sin(this.lastTime * 0.015) * 1.0;
        
        this.ctx.save();
        this.ctx.translate(0, bounce);

        // Neck & Spine
        this.ctx.strokeStyle = '#fff';
        this.ctx.lineWidth = 3;
        this.ctx.beginPath();
        this.ctx.moveTo(-8, -14); // hip
        this.ctx.lineTo(-4, -25); // neck
        this.ctx.stroke();

        // Arms (steering wheel)
        this.ctx.strokeStyle = '#bbb';
        this.ctx.lineWidth = 2.5;
        this.ctx.beginPath();
        this.ctx.moveTo(-6, -21); // shoulder
        this.ctx.lineTo(8, -20);  // hands/wheel
        this.ctx.stroke();

        // Helmet
        this.ctx.beginPath();
        this.ctx.arc(-3, -31, 7, 0, Math.PI * 2);
        this.ctx.fillStyle = '#e2dfec';
        this.ctx.fill();

        // Helmet visor (cyan glow)
        this.ctx.beginPath();
        this.ctx.arc(0, -31, 4, -Math.PI/3, Math.PI/3);
        this.ctx.strokeStyle = '#00ffff';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();

        this.ctx.restore();
    }

    drawWheel(wheel) {
        const scale = this.camera.scale;
        const screenWheelX = (wheel.pos.x - this.camera.x) * scale + CANVAS_WIDTH * 0.3;
        const screenWheelY = CANVAS_HEIGHT * 0.65 - (wheel.pos.y - this.camera.y) * scale;
        
        this.ctx.save();
        
        // Translate to wheel screen position and scale
        this.ctx.translate(screenWheelX, screenWheelY);
        this.ctx.scale(scale, scale);
        // Rotate: -angle because canvas is flipped
        this.ctx.rotate(-wheel.angle);

        // 1. Draw outer black tire rubber
        const r = wheel.radius;
        this.ctx.beginPath();
        this.ctx.arc(0, 0, r, 0, Math.PI * 2);
        
        const tireGrad = this.ctx.createRadialGradient(0, 0, r - 8, 0, 0, r);
        tireGrad.addColorStop(0, '#221f2d');
        tireGrad.addColorStop(0.7, '#14121b');
        tireGrad.addColorStop(1, '#08070b');
        this.ctx.fillStyle = tireGrad;
        
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
        this.ctx.lineWidth = 1;
        this.ctx.fill();
        this.ctx.stroke();

        // 2. Draw tire tread details (notches along outer rim)
        this.ctx.strokeStyle = '#0a090e';
        this.ctx.lineWidth = 3.5;
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 6) {
            this.ctx.beginPath();
            this.ctx.moveTo(Math.cos(a) * (r - 4), Math.sin(a) * (r - 4));
            this.ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
            this.ctx.stroke();
        }

        // 3. Draw neon rim
        this.ctx.beginPath();
        this.ctx.arc(0, 0, r - 7, 0, Math.PI * 2);
        this.ctx.fillStyle = '#0f0e15';
        this.ctx.strokeStyle = '#9d4edd';
        this.ctx.lineWidth = 2.5;
        this.ctx.shadowColor = '#9d4edd';
        this.ctx.shadowBlur = wheel.onGround ? 12 : 5;
        this.ctx.fill();
        this.ctx.stroke();
        this.ctx.shadowBlur = 0; // reset

        // 4. Draw metal hub spokes (inside rim)
        this.ctx.strokeStyle = '#00ffff';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 3) {
            this.ctx.moveTo(0, 0);
            this.ctx.lineTo(Math.cos(a) * (r - 9), Math.sin(a) * (r - 9));
        }
        this.ctx.stroke();

        // 5. Draw center wheel hub nut
        this.ctx.beginPath();
        this.ctx.arc(0, 0, 3, 0, Math.PI * 2);
        this.ctx.fillStyle = '#fff';
        this.ctx.fill();

        this.ctx.restore();
    }

}

// Utility font fallback helper
function var_font_fallback() {
    return 'Outfit, sans-serif';
}

// Global initialization
window.addEventListener('DOMContentLoaded', () => {
    window.gameController = new GameController();
});
