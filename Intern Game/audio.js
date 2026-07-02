/**
 * Hill Climb Car Game - Audio Module (Web Audio API Synthesizer)
 * Creates real-time audio synthesis for engine RPM, coin pickups, upgrades, and crashes.
 */

class AudioController {
    constructor() {
        this.ctx = null;
        this.engineOsc1 = null;
        this.engineOsc2 = null;
        this.engineFilter = null;
        this.engineGain = null;
        this.isEngineRunning = false;
        
        // Settings
        this.baseFreq = 38; // Low fundamental frequency for motor idling
        this.muted = false;
    }

    init() {
        if (this.ctx) return;
        
        // Create audio context (handle browser autoplay restrictions on user interaction)
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextClass) return;

        try {
            this.ctx = new AudioContextClass();
        } catch (e) {
            console.error("Web Audio API not supported", e);
        }
    }

    resumeContext() {
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    startEngine() {
        this.init();
        this.resumeContext();
        if (!this.ctx || this.isEngineRunning || this.muted) return;

        try {
            // Create oscillators for engine cylinders
            this.engineOsc1 = this.ctx.createOscillator();
            this.engineOsc2 = this.ctx.createOscillator();
            
            // Sawtooth waves provide nice rich harmonics for engine hum
            this.engineOsc1.type = 'sawtooth';
            this.engineOsc2.type = 'triangle'; // adds low-end warmth

            // Sub-harmonic detune for richer sound
            this.engineOsc1.frequency.setValueAtTime(this.baseFreq, this.ctx.currentTime);
            this.engineOsc2.frequency.setValueAtTime(this.baseFreq * 1.5, this.ctx.currentTime);

            // Low-pass filter to make it sound like a muffled engine block rather than a harsh synth
            this.engineFilter = this.ctx.createBiquadFilter();
            this.engineFilter.type = 'lowpass';
            this.engineFilter.frequency.setValueAtTime(180, this.ctx.currentTime);
            this.engineFilter.Q.setValueAtTime(2.0, this.ctx.currentTime);

            // Volume gain node
            this.engineGain = this.ctx.createGain();
            this.engineGain.gain.setValueAtTime(0.0, this.ctx.currentTime); // start quiet
            
            // Connect: Oscs -> Filter -> Gain -> Output
            this.engineOsc1.connect(this.engineFilter);
            this.engineOsc2.connect(this.engineFilter);
            this.engineFilter.connect(this.engineGain);
            this.engineGain.connect(this.ctx.destination);

            // Start oscillators
            this.engineOsc1.start(0);
            this.engineOsc2.start(0);

            // Fade in engine
            this.engineGain.gain.linearRampToValueAtTime(0.22, this.ctx.currentTime + 0.3);

            this.isEngineRunning = true;
        } catch (e) {
            console.error("Failed to start engine audio", e);
        }
    }

    stopEngine() {
        if (!this.isEngineRunning) return;

        try {
            const now = this.ctx.currentTime;
            this.engineGain.gain.cancelScheduledValues(now);
            this.engineGain.gain.setValueAtTime(this.engineGain.gain.value, now);
            this.engineGain.gain.linearRampToValueAtTime(0.0, now + 0.15);

            setTimeout(() => {
                if (this.engineOsc1) { this.engineOsc1.stop(); this.engineOsc1.disconnect(); }
                if (this.engineOsc2) { this.engineOsc2.stop(); this.engineOsc2.disconnect(); }
                if (this.engineFilter) this.engineFilter.disconnect();
                if (this.engineGain) this.engineGain.disconnect();
                this.isEngineRunning = false;
            }, 200);
        } catch (e) {
            this.isEngineRunning = false;
        }
    }

    updateEngine(rpmRatio, throttle) {
        if (!this.isEngineRunning || this.muted || !this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            // Map RPM to frequency (range: baseFreq to baseFreq * 4.5)
            const targetFreq1 = this.baseFreq * (1.0 + rpmRatio * 3.5);
            const targetFreq2 = targetFreq1 * 1.5;

            // Smoothly interpolate frequency changes
            this.engineOsc1.frequency.setTargetAtTime(targetFreq1, now, 0.05);
            this.engineOsc2.frequency.setTargetAtTime(targetFreq2, now, 0.05);

            // Open filter cutoff as RPM increases to make engine louder and brighter
            const targetCutoff = 160 + (rpmRatio * 450) + (throttle * 150);
            this.engineFilter.frequency.setTargetAtTime(targetCutoff, now, 0.08);

            // Modulate volume slightly based on throttle
            const targetGain = 0.16 + (throttle * 0.14) + (rpmRatio * 0.05);
            this.engineGain.gain.setTargetAtTime(targetGain, now, 0.1);
        } catch (e) {
            // Ignore Web Audio timing issues during tab switching
        }
    }

    playCoin() {
        this.init();
        this.resumeContext();
        if (this.muted || !this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            // Classic retro double chime (987.77 Hz = B5, then 1318.51 Hz = E6)
            osc.frequency.setValueAtTime(987.77, now);
            osc.frequency.setValueAtTime(1318.51, now + 0.08);

            gain.gain.setValueAtTime(0.0, now);
            gain.gain.linearRampToValueAtTime(0.12, now + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.4);
        } catch (e) {}
    }

    playFuel() {
        this.init();
        this.resumeContext();
        if (this.muted || !this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            // Bubbling upward pitch sweep
            osc.frequency.setValueAtTime(300, now);
            osc.frequency.exponentialRampToValueAtTime(1200, now + 0.3);

            gain.gain.setValueAtTime(0.0, now);
            gain.gain.linearRampToValueAtTime(0.15, now + 0.05);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.45);
        } catch (e) {}
    }

    playUpgrade() {
        this.init();
        this.resumeContext();
        if (this.muted || !this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            const osc1 = this.ctx.createOscillator();
            const osc2 = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc1.type = 'triangle';
            osc2.type = 'sine';

            osc1.frequency.setValueAtTime(523.25, now); // C5
            osc1.frequency.setValueAtTime(659.25, now + 0.08); // E5
            osc1.frequency.setValueAtTime(783.99, now + 0.16); // G5
            osc1.frequency.setValueAtTime(1046.50, now + 0.24); // C6

            osc2.frequency.setValueAtTime(523.25 * 1.5, now);
            osc2.frequency.setValueAtTime(659.25 * 1.5, now + 0.08);
            osc2.frequency.setValueAtTime(783.99 * 1.5, now + 0.16);
            osc2.frequency.setValueAtTime(1046.50 * 1.5, now + 0.24);

            gain.gain.setValueAtTime(0.0, now);
            gain.gain.linearRampToValueAtTime(0.15, now + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.55);

            osc1.connect(gain);
            osc2.connect(gain);
            gain.connect(this.ctx.destination);

            osc1.start(now);
            osc2.start(now);
            osc1.stop(now + 0.6);
            osc2.stop(now + 0.6);
        } catch (e) {}
    }

    playCrash() {
        this.init();
        this.resumeContext();
        if (this.muted || !this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            
            // Noise synthesis for metal crash/rumble
            const bufferSize = this.ctx.sampleRate * 1.5; // 1.5 seconds of noise
            const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
            const data = buffer.getChannelData(0);
            
            // Fill buffer with white noise
            for (let i = 0; i < bufferSize; i++) {
                data[i] = Math.random() * 2 - 1;
            }

            const noiseNode = this.ctx.createBufferSource();
            noiseNode.buffer = buffer;

            // Create low-pass filter to shape noise to a rumble
            const filter = this.ctx.createBiquadFilter();
            filter.type = 'lowpass';
            filter.frequency.setValueAtTime(400, now);
            filter.frequency.exponentialRampToValueAtTime(30, now + 1.2);

            const gain = this.ctx.createGain();
            gain.gain.setValueAtTime(0.28, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 1.3);

            // Connect nodes
            noiseNode.connect(filter);
            filter.connect(gain);
            gain.connect(this.ctx.destination);

            noiseNode.start(now);
            noiseNode.stop(now + 1.4);

            // Add a brief low pitch square wave sweep for a metal impact thud
            const synth = this.ctx.createOscillator();
            const synthGain = this.ctx.createGain();
            synth.type = 'sawtooth';
            synth.frequency.setValueAtTime(140, now);
            synth.frequency.linearRampToValueAtTime(20, now + 0.25);

            synthGain.gain.setValueAtTime(0.3, now);
            synthGain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

            synth.connect(synthGain);
            synthGain.connect(this.ctx.destination);

            synth.start(now);
            synth.stop(now + 0.35);
        } catch (e) {}
    }

    playClick() {
        this.init();
        this.resumeContext();
        if (this.muted || !this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(600, now);
            osc.frequency.exponentialRampToValueAtTime(150, now + 0.05);

            gain.gain.setValueAtTime(0.05, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.08);
        } catch (e) {}
    }

    toggleMute() {
        this.muted = !this.muted;
        if (this.muted) {
            this.stopEngine();
        } else {
            this.startEngine();
        }
        return this.muted;
    }
}

// Global audio singleton
const gameAudio = new AudioController();
window.gameAudio = gameAudio;
