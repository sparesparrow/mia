// Universal AI-SERVIS Web Page JavaScript
// Professional, clean interactions with smooth animations

document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

function initializePage() {
    setupLanguageSwitcher();
    setupNavigation();
    setupScrollAnimations();
    setupMobileMenu();
    setupFormValidation();
    setupAnalytics();
}

// Language Switching
function setupLanguageSwitcher() {
    const langButtons = document.querySelectorAll('.lang-btn');

    langButtons.forEach(button => {
        button.addEventListener('click', function() {
            const lang = this.getAttribute('data-lang');

            // Update button states
            langButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            // Use the i18n system to switch language
            if (window.i18n) {
                window.i18n.switchLanguage(lang);
            }
        });
    });
}

// Navigation
function setupNavigation() {
    const navbar = document.querySelector('.navbar');
    const navLinks = document.querySelectorAll('.nav-menu a');

    // Navbar scroll effect
    window.addEventListener('scroll', function() {
        if (window.scrollY > 100) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Smooth scrolling for anchor links
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);

            if (targetSection) {
                const offsetTop = targetSection.offsetTop - 80; // Account for fixed navbar
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Mobile Menu
function setupMobileMenu() {
    const mobileToggle = document.querySelector('.mobile-menu-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener('click', function() {
            navMenu.classList.toggle('mobile-open');
            this.classList.toggle('active');

            // Animate hamburger icon
            const spans = this.querySelectorAll('span');
            if (this.classList.contains('active')) {
                spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });
    }
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

    // Observe elements for animation
    const animateElements = document.querySelectorAll('.feature-card, .use-case, .pricing-card, .tech-card');
    animateElements.forEach(element => {
        observer.observe(element);
    });
}

// Form Validation and Interactions
function setupFormValidation() {
    // Demo request buttons
    const demoButtons = document.querySelectorAll('button[data-i18n*="demo"], button[data-i18n*="Demo"]');
    demoButtons.forEach(button => {
        button.addEventListener('click', function() {
            showDemoModal();
        });
    });

    // CTA buttons
    const ctaButtons = document.querySelectorAll('.cta-btn');
    ctaButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.textContent.includes('Demo') || this.textContent.includes('demo')) {
                showDemoModal();
            }
        });
    });
}

function showDemoModal() {
    // Create modal for demo requests
    const modal = document.createElement('div');
    modal.className = 'demo-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3 data-i18n="schedule-demo" data-i18n-ns="common">Schedule Your Demo</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <form class="demo-form">
                    <div class="form-group">
                        <label data-i18n="company-name" data-i18n-ns="common">Company Name</label>
                        <input type="text" name="company" required>
                    </div>
                    <div class="form-group">
                        <label data-i18n="contact-person" data-i18n-ns="common">Contact Person</label>
                        <input type="text" name="contact" required>
                    </div>
                    <div class="form-group">
                        <label data-i18n="email" data-i18n-ns="common">Email</label>
                        <input type="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label data-i18n="phone" data-i18n-ns="common">Phone</label>
                        <input type="tel" name="phone">
                    </div>
                    <div class="form-group">
                        <label data-i18n="fleet-size" data-i18n-ns="common">Fleet Size</label>
                        <select name="fleet_size">
                            <option value="1-5" data-i18n="1-5-vehicles" data-i18n-ns="common">1-5 vehicles</option>
                            <option value="6-20" data-i18n="6-20-vehicles" data-i18n-ns="common">6-20 vehicles</option>
                            <option value="21-100" data-i18n="21-100-vehicles" data-i18n-ns="common">21-100 vehicles</option>
                            <option value="100+" data-i18n="100-vehicles" data-i18n-ns="common">100+ vehicles</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label data-i18n="preferred-demo-date" data-i18n-ns="common">Preferred Demo Date</label>
                        <input type="date" name="demo_date">
                    </div>
                    <button type="submit" class="btn btn-primary" data-i18n="request-demo" data-i18n-ns="common">Request Demo</button>
                </form>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Setup modal interactions
    const closeBtn = modal.querySelector('.modal-close');
    const form = modal.querySelector('.demo-form');

    closeBtn.addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        handleDemoRequest(new FormData(this));
        modal.remove();
    });

    // Update form labels based on current language
    updateModalLanguage(modal);
}

function updateModalLanguage(modal) {
    const currentLang = document.querySelector('.lang-btn.active').getAttribute('data-lang');
    const elements = modal.querySelectorAll('[data-i18n]');

    elements.forEach(element => {
        const key = element.getAttribute('data-i18n');
        const namespace = element.getAttribute('data-i18n-ns') || 'common';
        
        if (key && window.i18n) {
            const translation = window.i18n.t(key, namespace);
            
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.placeholder = translation;
            } else {
                element.textContent = translation;
            }
        }
    });
}

function handleDemoRequest(formData) {
    // Simulate form submission
    console.log('Demo request submitted:', Object.fromEntries(formData));

    // Show success message
    showNotification('Demo request submitted successfully! We\'ll contact you within 24 hours.', 'success');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Analytics and Tracking
function setupAnalytics() {
    // Track button clicks
    const trackableButtons = document.querySelectorAll('button, .btn');
    trackableButtons.forEach(button => {
        button.addEventListener('click', function() {
            const buttonText = this.textContent.trim();
            trackEvent('button_click', {
                button_text: buttonText,
                page_location: window.location.pathname
            });
        });
    });

    // Track form submissions
    document.addEventListener('submit', function(e) {
        trackEvent('form_submit', {
            form_type: e.target.className,
            page_location: window.location.pathname
        });
    });

    // Track scroll depth
    let maxScroll = 0;
    window.addEventListener('scroll', function() {
        const scrollPercent = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
        if (scrollPercent > maxScroll && scrollPercent % 25 === 0) {
            maxScroll = scrollPercent;
            trackEvent('scroll_depth', { percent: scrollPercent });
        }
    });
}

function trackEvent(eventName, properties = {}) {
    // In a real implementation, you would send this to your analytics service
    console.log('Analytics event:', eventName, properties);

    // Example: Google Analytics, Mixpanel, etc.
    // gtag('event', eventName, properties);
    // mixpanel.track(eventName, properties);
}

// Modal Styles (added dynamically)
const modalStyles = `
    .demo-modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease-out;
    }

    .modal-content {
        background: white;
        border-radius: 12px;
        max-width: 500px;
        width: 90%;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }

    .modal-header {
        padding: 1.5rem;
        border-bottom: 1px solid #e2e8f0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .modal-header h3 {
        margin: 0;
        color: #1a365d;
        font-size: 1.25rem;
        font-weight: 600;
    }

    .modal-close {
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        color: #718096;
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
        background: #f7fafc;
        color: #1a202c;
    }

    .modal-body {
        padding: 1.5rem;
    }

    .demo-form {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .form-group label {
        font-weight: 500;
        color: #2d3748;
        font-size: 0.875rem;
    }

    .form-group input,
    .form-group select {
        padding: 0.75rem;
        border: 2px solid #e2e8f0;
        border-radius: 6px;
        font-size: 1rem;
        transition: border-color 0.2s;
    }

    .form-group input:focus,
    .form-group select:focus {
        outline: none;
        border-color: #3182ce;
    }

    .notification {
        position: fixed;
        top: 1rem;
        right: 1rem;
        background: #38a169;
        color: white;
        padding: 1rem;
        border-radius: 6px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        z-index: 10001;
        transform: translateX(100%);
        transition: transform 0.3s ease-out;
        max-width: 400px;
    }

    .notification.show {
        transform: translateX(0);
    }

    .notification-success {
        background: #38a169;
    }

    .notification-error {
        background: #e53e3e;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @media (max-width: 768px) {
        .modal-content {
            margin: 1rem;
            width: calc(100% - 2rem);
        }
    }
`;

// Add modal styles to page
const styleSheet = document.createElement('style');
styleSheet.textContent = modalStyles;
document.head.appendChild(styleSheet);

// Mobile navigation styles
const mobileStyles = `
    .nav-menu.mobile-open {
        display: flex;
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        flex-direction: column;
        padding: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-top: 1px solid #e2e8f0;
    }

    .nav-menu.mobile-open a {
        padding: 0.75rem 0;
        border-bottom: 1px solid #f7fafc;
    }

    .nav-menu.mobile-open a:last-child {
        border-bottom: none;
    }

    @media (max-width: 768px) {
        .container {
            padding: 0 1rem;
        }

        .nav-brand {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .mobile-menu-toggle.active span:nth-child(1) {
            transform: rotate(45deg) translate(5px, 5px);
        }

        .mobile-menu-toggle.active span:nth-child(2) {
            opacity: 0;
        }

        .mobile-menu-toggle.active span:nth-child(3) {
            transform: rotate(-45deg) translate(7px, -6px);
        }
    }
`;

const mobileStyleSheet = document.createElement('style');
mobileStyleSheet.textContent = mobileStyles;
document.head.appendChild(mobileStyleSheet);

// Performance optimization: Lazy load images
function setupLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');

    const imageObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));
}

// Initialize lazy loading
setupLazyLoading();

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    trackEvent('javascript_error', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno
    });
});

// Service worker registration (for PWA features)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // navigator.serviceWorker.register('/sw.js')
        //     .then(registration => console.log('SW registered'))
        //     .catch(error => console.log('SW registration failed'));
    });
}
