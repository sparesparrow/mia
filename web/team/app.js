// AI-SERVIS Team Portal JavaScript
// Professional internal tools and real-time monitoring

document.addEventListener('DOMContentLoaded', function() {
    initializeTeamPortal();
});

function initializeTeamPortal() {
    setupNavigation();
    setupThemeToggle();
    setupUserMenu();
    setupRealTimeUpdates();
    setupModuleInteractions();
    setupScrollAnimations();
    setupKeyboardShortcuts();
}

// Navigation
function setupNavigation() {
    const navLinks = document.querySelectorAll('.team-nav .nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            // Update active state
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');

            // Smooth scroll to section
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);

            if (targetSection) {
                const offsetTop = targetSection.offsetTop - 100;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Update active nav on scroll
    window.addEventListener('scroll', function() {
        const sections = document.querySelectorAll('.section');
        const scrollPosition = window.scrollY + 150;

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${sectionId}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    });
}

// Theme Toggle
function setupThemeToggle() {
    const themeBtn = document.querySelector('.btn-secondary');
    const body = document.body;

    // Load saved theme
    const savedTheme = localStorage.getItem('team-theme') || 'dark';
    if (savedTheme === 'light') {
        body.classList.add('light-theme');
        updateThemeIcon(themeBtn, 'light');
    } else {
        updateThemeIcon(themeBtn, 'dark');
    }

    themeBtn.addEventListener('click', function() {
        body.classList.toggle('light-theme');
        const isLight = body.classList.contains('light-theme');
        const theme = isLight ? 'light' : 'dark';

        localStorage.setItem('team-theme', theme);
        updateThemeIcon(this, theme);
    });
}

function updateThemeIcon(button, theme) {
    const icon = button.querySelector('i');
    icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
}

// User Menu
function setupUserMenu() {
    const userBtn = document.querySelector('.user-btn');
    const dropdown = document.querySelector('.user-dropdown');

    userBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function() {
        dropdown.style.display = 'none';
    });

    // Handle menu actions
    const menuItems = dropdown.querySelectorAll('a');
    menuItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.textContent.toLowerCase();

            switch(action) {
                case 'profile':
                    showProfileModal();
                    break;
                case 'settings':
                    showSettingsModal();
                    break;
                case 'logout':
                    handleLogout();
                    break;
            }
        });
    });
}

// Real-time Updates
function setupRealTimeUpdates() {
    // Update status timestamps
    updateTimestamps();

    // Simulate real-time status updates
    setInterval(updateSystemStatus, 30000); // Update every 30 seconds

    // Update last update time
    setInterval(() => {
        const lastUpdate = document.getElementById('lastUpdate');
        if (lastUpdate) {
            lastUpdate.textContent = 'just now';
            setTimeout(() => {
                lastUpdate.textContent = '1 minute ago';
            }, 60000);
        }
    }, 60000);
}

function updateTimestamps() {
    const logEntries = document.querySelectorAll('.log-entry');
    logEntries.forEach(entry => {
        const timeElement = entry.querySelector('.log-time');
        if (timeElement) {
            // In a real app, these would be actual timestamps
            const now = new Date();
            const randomMinutes = Math.floor(Math.random() * 60);
            now.setMinutes(now.getMinutes() - randomMinutes);
            timeElement.textContent = now.toTimeString().split(' ')[0];
        }
    });
}

function updateSystemStatus() {
    // Simulate status changes
    const statusDots = document.querySelectorAll('.status-dot');

    statusDots.forEach(dot => {
        // Small chance of status change for realism
        if (Math.random() < 0.1) {
            const statuses = ['status-healthy', 'status-warning', 'status-error'];
            const currentStatus = Array.from(dot.classList).find(cls => cls.startsWith('status-'));
            let newStatus = statuses[Math.floor(Math.random() * statuses.length)];

            // Ensure we don't break the system too often
            if (currentStatus === 'status-healthy' && Math.random() < 0.8) {
                newStatus = 'status-healthy';
            }

            dot.className = `status-dot ${newStatus}`;

            // Update corresponding service status
            const statusElement = dot.closest('.status-item') || dot.closest('.module-status') || dot.closest('.member-status');
            if (statusElement) {
                const statusText = statusElement.querySelector('span:last-child, .service-status');
                if (statusText) {
                    statusText.textContent = getStatusText(newStatus);
                    statusText.className = `service-status ${newStatus}`;
                }
            }
        }
    });

    // Update health score
    updateHealthScore();
}

function getStatusText(statusClass) {
    const statusMap = {
        'status-healthy': 'Active',
        'status-warning': 'Warning',
        'status-error': 'Error'
    };
    return statusMap[statusClass] || 'Unknown';
}

function updateHealthScore() {
    const scoreElement = document.querySelector('.score-value');
    if (scoreElement) {
        const currentScore = parseFloat(scoreElement.textContent);
        const variation = (Math.random() - 0.5) * 0.4; // ±0.2 variation
        const newScore = Math.max(95, Math.min(100, currentScore + variation));

        scoreElement.textContent = newScore.toFixed(1) + '%';

        // Update the conic gradient
        const scoreCircle = scoreElement.closest('.score-circle');
        if (scoreCircle) {
            scoreCircle.style.background = `conic-gradient(var(--success-color) ${newScore}%, var(--bg-tertiary) 0deg)`;
        }
    }
}

// Module Interactions
function setupModuleInteractions() {
    const moduleCards = document.querySelectorAll('.module-card');

    moduleCards.forEach(card => {
        card.addEventListener('click', function() {
            const moduleName = this.getAttribute('data-module');
            showModuleDetails(moduleName);
        });

        // Add hover effects
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

function showModuleDetails(moduleName) {
    const moduleData = {
        'core-orchestrator': {
            title: 'Core Orchestrator Details',
            description: 'The central nervous system of AI-SERVIS, coordinating all AI modules through the Model Context Protocol.',
            endpoints: ['POST /api/voice', 'GET /api/health', 'GET /api/services'],
            dependencies: ['ai-audio-assistant', 'service-discovery', 'ai-platform-controllers'],
            metrics: { requests: '1.2k/min', latency: '45ms', errors: '0.01%' }
        },
        'ai-audio-assistant': {
            title: 'AI Audio Assistant Details',
            description: 'Voice processing and music control with ElevenLabs TTS integration and multi-zone audio support.',
            endpoints: ['POST /api/audio/play', 'GET /api/audio/status', 'PUT /api/audio/volume'],
            dependencies: ['elevenlabs-api', 'audio-drivers', 'mqtt-broker'],
            metrics: { tracks: '450/day', voice_calls: '89/hour', uptime: '98.5%' }
        },
        'service-discovery': {
            title: 'Service Discovery Details',
            description: 'Dynamic service registration and health monitoring for the microservices architecture.',
            endpoints: ['POST /api/register', 'GET /api/services', 'DELETE /api/unregister'],
            dependencies: ['redis', 'mqtt-broker'],
            metrics: { services: '6', checks: '120/min', failures: '2/hour' }
        },
        'ai-platform-controllers': {
            title: 'Platform Controllers Details',
            description: 'Cross-platform system management for Linux environments with secure command execution.',
            endpoints: ['POST /api/execute', 'GET /api/processes', 'POST /api/files'],
            dependencies: ['system-apis', 'security-module'],
            metrics: { commands: '340/hour', processes: '45', files: '1200' }
        }
    };

    const data = moduleData[moduleName];
    if (!data) return;

    const modal = document.createElement('div');
    modal.className = 'module-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>${data.title}</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <p>${data.description}</p>

                <div class="modal-section">
                    <h4>API Endpoints</h4>
                    <ul>
                        ${data.endpoints.map(endpoint => `<li><code>${endpoint}</code></li>`).join('')}
                    </ul>
                </div>

                <div class="modal-section">
                    <h4>Dependencies</h4>
                    <div class="dependency-tags">
                        ${data.dependencies.map(dep => `<span class="tech-tag">${dep}</span>`).join('')}
                    </div>
                </div>

                <div class="modal-section">
                    <h4>Live Metrics</h4>
                    <div class="metrics-grid">
                        ${Object.entries(data.metrics).map(([key, value]) =>
                            `<div class="metric"><span class="metric-value">${value}</span><span class="metric-label">${key}</span></div>`
                        ).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    const closeBtn = modal.querySelector('.modal-close');
    closeBtn.addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

// Scroll Animations
function setupScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
            }
        });
    }, observerOptions);

    // Observe sections and cards
    const animateElements = document.querySelectorAll('.section, .module-card, .team-member, .doc-card');
    animateElements.forEach(element => {
        observer.observe(element);
    });
}

// Keyboard Shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            showSearchModal();
        }

        // Ctrl/Cmd + , for settings
        if ((e.ctrlKey || e.metaKey) && e.key === ',') {
            e.preventDefault();
            showSettingsModal();
        }

        // Escape to close modals
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

// Modal Functions
function showProfileModal() {
    const modal = createModal('User Profile', `
        <div class="profile-info">
            <div class="profile-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="profile-details">
                <h3>sparesparrow</h3>
                <p>Lead Developer & Architect</p>
                <p>sparesparrow@protonmail.ch</p>
            </div>
        </div>
        <div class="profile-stats">
            <div class="stat">
                <span class="stat-value">247</span>
                <span class="stat-label">Commits</span>
            </div>
            <div class="stat">
                <span class="stat-value">89</span>
                <span class="stat-label">Issues</span>
            </div>
            <div class="stat">
                <span class="stat-value">156</span>
                <span class="stat-label">PRs</span>
            </div>
        </div>
    `);
    document.body.appendChild(modal);
}

function showSettingsModal() {
    const modal = createModal('Team Settings', `
        <div class="settings-section">
            <h4>Notifications</h4>
            <label class="setting-item">
                <input type="checkbox" checked> System alerts
            </label>
            <label class="setting-item">
                <input type="checkbox" checked> Module status changes
            </label>
            <label class="setting-item">
                <input type="checkbox"> Build notifications
            </label>
        </div>

        <div class="settings-section">
            <h4>Theme</h4>
            <select id="theme-select">
                <option value="dark">Dark</option>
                <option value="light">Light</option>
            </select>
        </div>

        <div class="settings-section">
            <h4>Auto-refresh</h4>
            <select id="refresh-select">
                <option value="30">Every 30 seconds</option>
                <option value="60">Every minute</option>
                <option value="300">Every 5 minutes</option>
            </select>
        </div>
    `);

    // Setup theme change
    const themeSelect = modal.querySelector('#theme-select');
    const currentTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
    themeSelect.value = currentTheme;

    themeSelect.addEventListener('change', function() {
        const themeBtn = document.querySelector('.btn-secondary');
        if (this.value === 'light') {
            document.body.classList.add('light-theme');
            updateThemeIcon(themeBtn, 'light');
        } else {
            document.body.classList.remove('light-theme');
            updateThemeIcon(themeBtn, 'dark');
        }
        localStorage.setItem('team-theme', this.value);
    });

    document.body.appendChild(modal);
}

function showSearchModal() {
    const modal = createModal('Search Team Portal', `
        <div class="search-container">
            <input type="text" placeholder="Search modules, docs, team members..." autofocus>
            <div class="search-results">
                <div class="search-result">
                    <i class="fas fa-code"></i>
                    <span>Core Orchestrator API</span>
                </div>
                <div class="search-result">
                    <i class="fas fa-music"></i>
                    <span>AI Audio Assistant</span>
                </div>
                <div class="search-result">
                    <i class="fas fa-cog"></i>
                    <span>Platform Controllers</span>
                </div>
            </div>
        </div>
    `);
    document.body.appendChild(modal);
}

function createModal(title, content) {
    const modal = document.createElement('div');
    modal.className = 'team-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>${title}</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                ${content}
            </div>
        </div>
    `;

    const closeBtn = modal.querySelector('.modal-close');
    closeBtn.addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });

    return modal;
}

function closeAllModals() {
    const modals = document.querySelectorAll('.team-modal, .module-modal');
    modals.forEach(modal => modal.remove());
}

function handleLogout() {
    // Simulate logout
    showNotification('Logged out successfully', 'success');
    setTimeout(() => {
        // In a real app, redirect to login
        console.log('User logged out');
    }, 1000);
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `team-notification notification-${type}`;
    notification.innerHTML = `<span class="notification-icon">${getNotificationIcon(type)}</span>${message}`;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function getNotificationIcon(type) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    return icons[type] || '📢';
}

function toggleUserMenu() {
    const dropdown = document.getElementById('userDropdown');
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
}

// Modal Styles
const modalStyles = `
    .team-modal, .module-modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(15, 23, 42, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        backdrop-filter: blur(4px);
        animation: modalFadeIn 0.2s ease-out;
    }

    .team-modal .modal-content, .module-modal .modal-content {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        max-width: 500px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
        animation: modalSlideIn 0.3s ease-out;
    }

    .modal-header {
        padding: 1.5rem;
        border-bottom: 1px solid var(--border-color);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .modal-header h3 {
        margin: 0;
        color: var(--accent-color);
        font-size: 1.25rem;
        font-weight: 600;
    }

    .modal-close {
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        color: var(--text-light);
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: all 0.2s;
    }

    .modal-close:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
    }

    .modal-body {
        padding: 1.5rem;
    }

    .profile-info {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .profile-avatar {
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, var(--accent-color), var(--accent-light));
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--bg-primary);
        font-size: 1.5rem;
    }

    .profile-details h3 {
        margin: 0 0 0.25rem 0;
        color: var(--text-primary);
    }

    .profile-details p {
        margin: 0.25rem 0;
        color: var(--text-light);
        font-size: 0.875rem;
    }

    .profile-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }

    .profile-stats .stat {
        text-align: center;
        padding: 1rem;
        background: var(--bg-tertiary);
        border-radius: 8px;
    }

    .profile-stats .stat-value {
        display: block;
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--accent-color);
        font-family: var(--font-family-mono);
    }

    .profile-stats .stat-label {
        font-size: 0.75rem;
        color: var(--text-light);
        margin-top: 0.25rem;
    }

    .settings-section {
        margin-bottom: 1.5rem;
    }

    .settings-section h4 {
        color: var(--text-primary);
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }

    .setting-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
        cursor: pointer;
    }

    .setting-item input[type="checkbox"] {
        width: 16px;
        height: 16px;
        accent-color: var(--accent-color);
    }

    .setting-item span {
        color: var(--text-light);
    }

    .settings-section select {
        width: 100%;
        padding: 0.5rem;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        color: var(--text-primary);
        font-size: 0.875rem;
    }

    .search-container input {
        width: 100%;
        padding: 0.75rem;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary);
        font-size: 1rem;
        margin-bottom: 1rem;
    }

    .search-container input:focus {
        outline: none;
        border-color: var(--accent-color);
    }

    .search-result {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.2s;
    }

    .search-result:hover {
        background: var(--bg-tertiary);
    }

    .search-result i {
        color: var(--accent-color);
    }

    .search-result span {
        color: var(--text-light);
    }

    .modal-section {
        margin-bottom: 1.5rem;
    }

    .modal-section h4 {
        color: var(--text-primary);
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }

    .modal-section ul {
        list-style: none;
        padding: 0;
    }

    .modal-section li {
        padding: 0.5rem 0;
        font-family: var(--font-family-mono);
        font-size: 0.875rem;
        color: var(--text-light);
    }

    .dependency-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
        gap: 1rem;
    }

    .metrics-grid .metric {
        text-align: center;
        padding: 0.75rem;
        background: var(--bg-tertiary);
        border-radius: 6px;
    }

    .metrics-grid .metric-value {
        display: block;
        font-size: 1.125rem;
        font-weight: 700;
        color: var(--accent-color);
        font-family: var(--font-family-mono);
    }

    .metrics-grid .metric-label {
        font-size: 0.75rem;
        color: var(--text-light);
    }

    .team-notification {
        position: fixed;
        top: 1rem;
        right: 1rem;
        background: linear-gradient(135deg, var(--success-color), var(--accent-color));
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        z-index: 10001;
        transform: translateX(100%);
        transition: transform 0.3s ease-out;
        max-width: 400px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
    }

    .team-notification.show {
        transform: translateX(0);
    }

    .notification-icon {
        font-size: 1rem;
    }

    @keyframes modalFadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes modalSlideIn {
        from {
            opacity: 0;
            transform: scale(0.9) translateY(-20px);
        }
        to {
            opacity: 1;
            transform: scale(1) translateY(0);
        }
    }

    @media (max-width: 768px) {
        .team-modal .modal-content, .module-modal .modal-content {
            margin: 1rem;
            width: calc(100% - 2rem);
        }

        .profile-info {
            flex-direction: column;
            text-align: center;
        }

        .metrics-grid {
            grid-template-columns: 1fr;
        }
    }
`;

// Add modal styles to page
const modalStyleSheet = document.createElement('style');
modalStyleSheet.textContent = modalStyles;
document.head.appendChild(modalStyleSheet);

// Error handling
window.addEventListener('error', function(e) {
    console.error('Team portal error:', e.error);
    showNotification('An error occurred: ' + e.message, 'error');
});

// Performance optimization
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Debounce scroll events
window.addEventListener('scroll', debounce(function() {
    // Handle scroll-based updates here if needed
}, 100));

// Service worker registration (for offline capabilities)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // navigator.serviceWorker.register('/team-sw.js')
        //     .then(registration => console.log('Team SW registered'))
        //     .catch(error => console.log('Team SW registration failed'));
    });
}
