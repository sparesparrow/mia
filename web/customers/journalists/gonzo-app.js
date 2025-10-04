// GONZO APP JS - DIGITAL MADNESS CONTROLLER
// "The edge... there is no honest way to explain it because the only people who really know where it is are the ones who have gone over." - H.S.T.

class GonzoMadnessController {
    constructor() {
        this.paranoiaLevel = 73;
        this.maxParanoia = 100;
        this.glitchMode = false;
        this.panicMode = false;
        this.countdownInterval = null;
        this.randomEvents = [];
        this.backgroundMusic = null;
        this.isMusicPlaying = false;

        this.init();
    }

    init() {
        this.setupParanoiaMeter();
        this.setupGlitchEffects();
        this.setupPanicMode();
        this.setupScrollEffects();
        this.setupRandomMadness();
        this.setupEasterEggs();
        this.setupAudio();
        this.startMadness();

        console.log("%c🔥 GONZO MODE ACTIVATED 🔥", "color: #ff0040; font-size: 20px; font-weight: bold;");
        console.log("%c'The only way to deal with an unfree world is to become so absolutely free that your very existence is an act of rebellion.' - Albert Camus", "color: #00ffff; font-style: italic;");
    }

    setupParanoiaMeter() {
        const paranoiaFill = document.getElementById('paranoia-fill');
        const paranoiaValue = document.querySelector('.meter-value');

        // Random paranoia fluctuations
        setInterval(() => {
            if (!this.panicMode) {
                this.paranoiaLevel += (Math.random() - 0.5) * 10;
                this.paranoiaLevel = Math.max(0, Math.min(this.maxParanoia, this.paranoiaLevel));

                paranoiaFill.style.width = `${this.paranoiaLevel}%`;
                paranoiaValue.textContent = `${Math.floor(this.paranoiaLevel)}%`;

                // Trigger special effects at high paranoia
                if (this.paranoiaLevel > 85) {
                    this.triggerHighParanoiaMode();
                }
            }
        }, 2000 + Math.random() * 3000);
    }

    setupGlitchEffects() {
        const glitchOverlay = document.getElementById('glitch-overlay');

        // Random glitch bursts
        setInterval(() => {
            if (Math.random() < 0.3 && !this.panicMode) {
                this.triggerGlitchBurst();
            }
        }, 5000 + Math.random() * 10000);
    }

    triggerGlitchBurst() {
        const duration = 200 + Math.random() * 300;
        document.body.style.filter = 'hue-rotate(90deg) saturate(2) brightness(1.2)';

        setTimeout(() => {
            document.body.style.filter = 'none';
        }, duration);

        // Add screen shake
        document.body.style.animation = `glitch-shake ${duration}ms ease-in-out`;
        setTimeout(() => {
            document.body.style.animation = 'none';
        }, duration);
    }

    triggerHighParanoiaMode() {
        document.body.classList.add('high-paranoia');

        // Add paranoid messages
        this.showParanoidMessage([
            "Někdo sleduje tvé pohyby...",
            "System detected unusual activity",
            "Are you sure you're alone?",
            "They know you're here",
            "Connection monitored",
            "Data packet intercepted"
        ][Math.floor(Math.random() * 6)]);

        setTimeout(() => {
            document.body.classList.remove('high-paranoia');
        }, 3000);
    }

    showParanoidMessage(message) {
        const messageEl = document.createElement('div');
        messageEl.className = 'paranoid-message';
        messageEl.textContent = message;
        messageEl.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255, 0, 64, 0.9);
            color: white;
            padding: 20px 40px;
            border-radius: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.2rem;
            font-weight: bold;
            z-index: 10000;
            text-align: center;
            box-shadow: 0 0 30px rgba(255, 0, 64, 0.8);
            animation: paranoid-fade-in 0.5s ease-out;
        `;

        document.body.appendChild(messageEl);

        setTimeout(() => {
            messageEl.style.animation = 'paranoid-fade-out 0.5s ease-in forwards';
            setTimeout(() => messageEl.remove(), 500);
        }, 2000);
    }

    setupPanicMode() {
        const panicButton = document.querySelector('.panic-button');
        const panicOverlay = document.getElementById('panic-mode');
        const cancelButton = document.getElementById('cancel-panic');
        const countdownEl = document.getElementById('countdown');

        panicButton.addEventListener('click', () => {
            this.activatePanicMode();
        });

        cancelButton.addEventListener('click', () => {
            this.deactivatePanicMode();
        });

        // Konami code for emergency panic
        this.setupKonamiCode();
    }

    activatePanicMode() {
        if (this.panicMode) return;

        this.panicMode = true;
        const panicOverlay = document.getElementById('panic-mode');
        const countdownEl = document.getElementById('countdown');

        panicOverlay.classList.remove('hidden');
        document.body.classList.add('panic-mode');

        // Paranoia meter goes to 100%
        document.getElementById('paranoia-fill').style.width = '100%';
        document.querySelector('.meter-value').textContent = '100%';

        // Pause background music during panic mode
        if (this.isMusicPlaying) {
            this.pauseBackgroundMusic();
        }

        let countdown = 10;
        countdownEl.textContent = countdown;

        this.countdownInterval = setInterval(() => {
            countdown--;
            countdownEl.textContent = countdown;

            if (countdown <= 0) {
                this.selfDestruct();
            }
        }, 1000);

        // Add panic sound effect (if audio context is available)
        this.playPanicSound();
    }

    deactivatePanicMode() {
        if (!this.panicMode) return;

        this.panicMode = false;
        const panicOverlay = document.getElementById('panic-mode');

        panicOverlay.classList.add('hidden');
        document.body.classList.remove('panic-mode');

        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }

        // Reset paranoia to normal levels
        this.paranoiaLevel = 73;
        document.getElementById('paranoia-fill').style.width = '73%';
        document.querySelector('.meter-value').textContent = '73%';

        this.showParanoidMessage("Panic mode deaktivován. You're safe... for now.");
    }

    selfDestruct() {
        clearInterval(this.countdownInterval);

        // Dramatic self-destruct sequence
        document.body.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: #000;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-direction: column;
                color: #ff0040;
                font-family: 'Bebas Neue', sans-serif;
                text-align: center;
                z-index: 99999;
            ">
                <h1 style="font-size: 6rem; margin-bottom: 20px; animation: self-destruct-blink 0.5s infinite;">SYSTEM PURGED</h1>
                <p style="font-size: 2rem; margin-bottom: 40px;">All traces eliminated</p>
                <p style="font-size: 1.2rem; color: #00ffff;">You were never here</p>
                <button onclick="location.reload()" style="
                    background: linear-gradient(45deg, #ff0040, #ff6666);
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    font-size: 1.2rem;
                    margin-top: 40px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-family: 'Bebas Neue', sans-serif;
                ">RESURRECT SYSTEM</button>
            </div>
        `;

        // Add self-destruct animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes self-destruct-blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    setupScrollEffects() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = 'gonzo-reveal 0.8s ease-out forwards';

                    // Increase paranoia when entering certain sections
                    if (entry.target.classList.contains('weapon-card') ||
                        entry.target.classList.contains('story-card')) {
                        this.paranoiaLevel += 5;
                    }
                }
            });
        }, observerOptions);

        // Observe all major elements
        document.querySelectorAll('.weapon-card, .story-card, .price-card').forEach(el => {
            observer.observe(el);
        });
    }

    setupRandomMadness() {
        // Random chaos events
        setInterval(() => {
            if (Math.random() < 0.1 && !this.panicMode) {
                this.triggerRandomEvent();
            }
        }, 10000);

        // Mouse follower paranoia
        this.setupMouseParanoia();

        // Typing paranoia
        this.setupTypingParanoia();
    }

    triggerRandomEvent() {
        const events = [
            () => this.changePageTitle(),
            () => this.triggerGlitchBurst(),
            () => this.showParanoidMessage("Did you hear that?"),
            () => this.changeParanoiaMeter(),
            () => this.triggerScreenFlash()
        ];

        const randomEvent = events[Math.floor(Math.random() * events.length)];
        randomEvent();
    }

    changePageTitle() {
        const originalTitle = document.title;
        const paranoidTitles = [
            "THEY'RE WATCHING",
            "CONNECTION COMPROMISED",
            "SURVEILLANCE ACTIVE",
            "DIGITAL SHADOWS",
            "ARE YOU ALONE?",
            originalTitle
        ];

        const newTitle = paranoidTitles[Math.floor(Math.random() * paranoidTitles.length)];
        document.title = newTitle;

        setTimeout(() => {
            document.title = originalTitle;
        }, 3000);
    }

    changeParanoiaMeter() {
        this.paranoiaLevel += Math.random() * 20 - 10;
        this.paranoiaLevel = Math.max(0, Math.min(this.maxParanoia, this.paranoiaLevel));
    }

    triggerScreenFlash() {
        const flash = document.createElement('div');
        flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.3);
            z-index: 9998;
            pointer-events: none;
            animation: screen-flash 0.1s ease-out;
        `;

        document.body.appendChild(flash);
        setTimeout(() => flash.remove(), 100);
    }

    setupMouseParanoia() {
        let mouseIdleTimer;
        let lastMouseMove = 0;

        document.addEventListener('mousemove', (e) => {
            lastMouseMove = Date.now();

            // Clear existing timer
            if (mouseIdleTimer) {
                clearTimeout(mouseIdleTimer);
            }

            // Set new timer
            mouseIdleTimer = setTimeout(() => {
                if (!this.panicMode && Math.random() < 0.3) {
                    this.showParanoidMessage("Mouse activity detected");
                }
            }, 30000); // 30 seconds of inactivity

            // Random cursor effects
            if (Math.random() < 0.001) {
                document.body.style.cursor = 'none';
                setTimeout(() => {
                    document.body.style.cursor = 'crosshair';
                }, 1000);
            }
        });
    }

    setupTypingParanoia() {
        let keyCount = 0;

        document.addEventListener('keydown', (e) => {
            keyCount++;

            // Every 50 keystrokes, increase paranoia
            if (keyCount % 50 === 0) {
                this.paranoiaLevel += 2;
                if (Math.random() < 0.5) {
                    this.showParanoidMessage("Keylogger detected");
                }
            }
        });
    }

    setupKonamiCode() {
        const konamiCode = [
            'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
            'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
            'KeyB', 'KeyA'
        ];
        let konamiIndex = 0;

        document.addEventListener('keydown', (e) => {
            if (e.code === konamiCode[konamiIndex]) {
                konamiIndex++;
                if (konamiIndex === konamiCode.length) {
                    this.activateSecretMode();
                    konamiIndex = 0;
                }
            } else {
                konamiIndex = 0;
            }
        });
    }

    activateSecretMode() {
        this.showParanoidMessage("🔥 GONZO SECRET MODE ACTIVATED 🔥");

        // Ultimate paranoia
        this.paranoiaLevel = 100;
        document.getElementById('paranoia-fill').style.width = '100%';
        document.querySelector('.meter-value').textContent = 'MAX';

        // Rainbow chaos mode
        document.body.style.animation = 'gonzo-rainbow 5s infinite';

        // Add secret content
        this.addSecretContent();

        setTimeout(() => {
            document.body.style.animation = 'none';
        }, 10000);
    }

    addSecretContent() {
        const secretMsg = document.createElement('div');
        secretMsg.innerHTML = `
            <div style="
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: rgba(0, 0, 0, 0.9);
                color: #00ffff;
                padding: 20px;
                border-radius: 10px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9rem;
                max-width: 300px;
                border: 2px solid #00ffff;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
                z-index: 9999;
                animation: secret-fade-in 1s ease-out;
            ">
                <h4 style="color: #ff0040; margin-bottom: 10px;">🕵️ CLASSIFIED INFO:</h4>
                <p>You've discovered the secret gonzo mode!</p>
                <p style="margin-top: 10px; font-size: 0.8rem; color: #ffff00;">
                    "The music business is a cruel and shallow money trench, a long plastic
                    hallway where thieves and pimps run free, and good men die like dogs."
                    - Hunter S. Thompson
                </p>
                <button onclick="this.parentElement.remove()" style="
                    background: #ff0040;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    margin-top: 10px;
                    border-radius: 3px;
                    cursor: pointer;
                    font-family: inherit;
                    font-size: 0.8rem;
                ">BURN AFTER READING</button>
            </div>
        `;

        document.body.appendChild(secretMsg);

        // Auto-remove after 15 seconds
        setTimeout(() => {
            if (secretMsg.parentElement) {
                secretMsg.remove();
            }
        }, 15000);
    }

    playPanicSound() {
        // Create audio context for panic sound
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();

            // Generate alarm-like sound
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(400, audioContext.currentTime + 0.5);

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (error) {
            console.log("Audio context not available - silent panic mode");
        }
    }

    setupAudio() {
        this.backgroundMusic = document.getElementById('background-music');
        
        if (!this.backgroundMusic) {
            console.log("Background music element not found");
            return;
        }
        
        // Set volume to a reasonable level (25% for gonzo atmosphere)
        this.backgroundMusic.volume = 0.25;
        
        // Try to autoplay when user first interacts with the page
        document.addEventListener('click', () => {
            if (!this.isMusicPlaying && this.backgroundMusic.paused) {
                this.playBackgroundMusic();
            }
        }, { once: true });
        
        // Handle audio toggle button
        const audioToggle = document.getElementById('audio-toggle');
        if (audioToggle) {
            audioToggle.addEventListener('click', () => this.toggleBackgroundMusic());
        }
        
        // Update button state based on audio state
        this.updateAudioButtonState();
        
        // Try autoplay on page load (may be blocked by browser)
        setTimeout(() => {
            this.playBackgroundMusic();
        }, 1000);
    }

    playBackgroundMusic() {
        if (this.backgroundMusic && this.backgroundMusic.paused) {
            this.backgroundMusic.play().then(() => {
                this.isMusicPlaying = true;
                this.updateAudioButtonState();
                console.log('🔥 Gonzo background music started');
                this.showParanoidMessage("🎵 Digital resistance soundtrack activated");
            }).catch(error => {
                console.log('Autoplay prevented by browser:', error);
                // Show a subtle indicator that music is available
                const audioToggle = document.getElementById('audio-toggle');
                if (audioToggle) {
                    audioToggle.style.opacity = '0.7';
                    audioToggle.title = 'Click to start gonzo soundtrack';
                }
            });
        }
    }

    pauseBackgroundMusic() {
        if (this.backgroundMusic && !this.backgroundMusic.paused) {
            this.backgroundMusic.pause();
            this.isMusicPlaying = false;
            this.updateAudioButtonState();
            console.log('Background music paused');
            this.showParanoidMessage("🔇 Soundtrack silenced");
        }
    }

    toggleBackgroundMusic() {
        if (this.isMusicPlaying) {
            this.pauseBackgroundMusic();
        } else {
            this.playBackgroundMusic();
        }
    }

    updateAudioButtonState() {
        const audioToggle = document.getElementById('audio-toggle');
        if (!audioToggle) return;
        
        if (this.isMusicPlaying) {
            audioToggle.textContent = '🔊';
            audioToggle.title = 'Pause gonzo soundtrack';
            audioToggle.style.opacity = '1';
            audioToggle.classList.add('playing');
        } else {
            audioToggle.textContent = '🎵';
            audioToggle.title = 'Play gonzo soundtrack';
            audioToggle.style.opacity = '0.7';
            audioToggle.classList.remove('playing');
        }
    }

    startMadness() {
        // Add dynamic styles
        const dynamicStyles = document.createElement('style');
        dynamicStyles.textContent = `
            @keyframes gonzo-reveal {
                from { opacity: 0; transform: translateY(30px) rotateX(20deg); }
                to { opacity: 1; transform: translateY(0) rotateX(0deg); }
            }

            @keyframes glitch-shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-2px) rotateZ(-0.5deg); }
                50% { transform: translateX(2px) rotateZ(0.5deg); }
                75% { transform: translateX(-1px) rotateZ(-0.25deg); }
            }

            @keyframes paranoid-fade-in {
                from { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
                to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            }

            @keyframes paranoid-fade-out {
                from { opacity: 1; transform: translate(-50%, -50%) scale(1); }
                to { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
            }

            @keyframes gonzo-rainbow {
                0% { filter: hue-rotate(0deg) saturate(1); }
                25% { filter: hue-rotate(90deg) saturate(1.5); }
                50% { filter: hue-rotate(180deg) saturate(2); }
                75% { filter: hue-rotate(270deg) saturate(1.5); }
                100% { filter: hue-rotate(360deg) saturate(1); }
            }

            @keyframes screen-flash {
                from { opacity: 0; }
                50% { opacity: 1; }
                to { opacity: 0; }
            }

            @keyframes secret-fade-in {
                from {
                    opacity: 0;
                    transform: translateX(100px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            .high-paranoia {
                filter: contrast(1.3) saturate(1.5) hue-rotate(10deg);
                animation: high-paranoia-shake 0.1s infinite;
            }

            @keyframes high-paranoia-shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-1px); }
                75% { transform: translateX(1px); }
            }
        `;

        document.head.appendChild(dynamicStyles);

        // Mark body as loaded
        document.body.classList.add('loaded');
        document.body.classList.remove('madness-loading');

        // Welcome message
        setTimeout(() => {
            if (!this.panicMode) {
                this.showParanoidMessage("Welcome to the Machine, pilgrim...");
            }
        }, 2000);

        console.log("🔥 Gonzo madness fully initialized. Reality distortion field active.");
    }
}

// Smooth scrolling for navigation
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const headerOffset = 100;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });

                // Increase paranoia when navigating
                if (window.gonzoController) {
                    window.gonzoController.paranoiaLevel += 3;
                }
            }
        });
    });
}

// Price card interactions
function setupPriceCards() {
    document.querySelectorAll('.price-card').forEach(card => {
        card.addEventListener('click', () => {
            // Remove previous selections
            document.querySelectorAll('.price-card').forEach(c =>
                c.classList.remove('selected'));

            // Add selection
            card.classList.add('selected');

            // Paranoia boost
            if (window.gonzoController) {
                window.gonzoController.paranoiaLevel += 5;
                window.gonzoController.showParanoidMessage(
                    "Choice recorded. Package selected for deployment."
                );
            }

            console.log('Resistance package selected:',
                card.querySelector('h3').textContent);
        });
    });
}

// Mobile menu for smaller screens
function setupMobileMenu() {
    // This would be more complex in a real implementation
    // For now, just log mobile interactions
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
        console.log("Mobile gonzo mode activated");

        // Adjust paranoia meter for mobile
        const paranoiaMeter = document.getElementById('paranoia-meter');
        if (paranoiaMeter) {
            paranoiaMeter.style.fontSize = '0.7rem';
        }
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Create global gonzo controller
    window.gonzoController = new GonzoMadnessController();

    // Initialize other features
    initSmoothScrolling();
    setupPriceCards();
    setupMobileMenu();

    // Add some initial chaos
    setTimeout(() => {
        if (Math.random() < 0.5) {
            window.gonzoController.triggerGlitchBurst();
        }
    }, 3000);

    console.log("%c🎭 GONZO JOURNALISM MODE: ACTIVE", "color: #ffff00; font-size: 16px; font-weight: bold;");
    console.log("%c'Buy the ticket, take the ride.' - Hunter S. Thompson", "color: #00ffff; font-style: italic;");
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (window.gonzoController) {
        if (document.hidden) {
            window.gonzoController.showParanoidMessage("Tab hidden - surveillance paused");
            window.gonzoController.paranoiaLevel -= 10;
        } else {
            window.gonzoController.showParanoidMessage("Welcome back, digital rebel");
            window.gonzoController.paranoiaLevel += 10;
        }
    }
});

// Handle window focus/blur
window.addEventListener('focus', () => {
    if (window.gonzoController && Math.random() < 0.3) {
        window.gonzoController.showParanoidMessage("System focus regained");
    }
});

window.addEventListener('blur', () => {
    if (window.gonzoController && Math.random() < 0.3) {
        window.gonzoController.showParanoidMessage("Focus lost - maintain vigilance");
    }
});

// Prevent right-click context menu (paranoia mode)
document.addEventListener('contextmenu', (e) => {
    if (window.gonzoController && window.gonzoController.paranoiaLevel > 80) {
        e.preventDefault();
        window.gonzoController.showParanoidMessage("Right-click disabled - security protocol active");
        return false;
    }
});

// Handle window resize for responsive madness
window.addEventListener('resize', () => {
    setupMobileMenu();

    if (window.gonzoController) {
        window.gonzoController.paranoiaLevel += 2;
    }
});

// Add CSS classes for selected elements
const addSelectedStyles = () => {
    const style = document.createElement('style');
    style.textContent = `
        .price-card.selected {
            border-color: #ffff00 !important;
            box-shadow: 0 0 40px rgba(255, 255, 0, 0.6) !important;
            transform: translateY(-10px) scale(1.03) !important;
        }

        .price-card.selected::before {
            opacity: 0.5 !important;
        }
    `;
    document.head.appendChild(style);
};

// Initialize selected styles
addSelectedStyles();
