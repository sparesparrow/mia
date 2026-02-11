// Language switching functionality
let currentLanguage = 'cs';

function switchLanguage(lang) {
    currentLanguage = lang;

    // Update active language button
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-lang') === lang) {
            btn.classList.add('active');
        }
    });

    // Update all translatable elements
    document.querySelectorAll('[data-en]').forEach(element => {
        const translation = element.getAttribute('data-' + lang);
        if (translation) {
            if (element.tagName === 'INPUT' && element.type === 'submit') {
                element.value = translation;
            } else if (element.hasAttribute('placeholder')) {
                element.placeholder = translation;
            } else if (element.hasAttribute('title')) {
                element.title = translation;
            } else {
                element.textContent = translation;
            }
        }
    });

    // Update document title and meta description
    const title = document.querySelector('title');
    const metaDescription = document.querySelector('meta[name="description"]');

    if (title) {
        const titleTranslation = title.getAttribute('data-' + lang);
        if (titleTranslation) {
            title.textContent = titleTranslation;
        }
    }

    if (metaDescription) {
        const descTranslation = metaDescription.getAttribute('data-' + lang);
        if (descTranslation) {
            metaDescription.setAttribute('content', descTranslation);
        }
    }

    // Update HTML lang attribute
    document.documentElement.setAttribute('lang', lang);

    // Store preference
    localStorage.setItem('preferred-language', lang);
}

// Smooth scrolling for navigation links
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const headerOffset = 80;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Scroll animations
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
            }
        });
    }, observerOptions);

    // Observe elements that should animate on scroll
    document.querySelectorAll('.feature-card, .use-case, .pricing-card, .tech-card').forEach(el => {
        observer.observe(el);
    });
}

// Navbar scroll effect
function initNavbarEffects() {
    const navbar = document.querySelector('.navbar');
    let lastScrollY = window.scrollY;

    window.addEventListener('scroll', () => {
        const currentScrollY = window.scrollY;

        if (currentScrollY > 100) {
            navbar.style.background = 'rgba(15, 15, 35, 0.95)';
        } else {
            navbar.style.background = 'rgba(15, 15, 35, 0.9)';
        }

        lastScrollY = currentScrollY;
    });
}

// Mobile menu functionality
function initMobileMenu() {
    const mobileToggle = document.querySelector('.mobile-menu-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener('click', () => {
            navMenu.classList.toggle('mobile-active');
            mobileToggle.classList.toggle('active');
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!mobileToggle.contains(e.target) && !navMenu.contains(e.target)) {
                navMenu.classList.remove('mobile-active');
                mobileToggle.classList.remove('active');
            }
        });
    }
}

// Pricing calculator (basic)
function initPricingCalculator() {
    const pricingCards = document.querySelectorAll('.pricing-card');

    pricingCards.forEach(card => {
        card.addEventListener('click', () => {
            // Remove active class from all cards
            pricingCards.forEach(c => c.classList.remove('selected'));
            // Add active class to clicked card
            card.classList.add('selected');

            // You could add more functionality here like opening a configuration modal
            console.log('Selected pricing tier:', card.querySelector('h3').textContent);
        });
    });
}

// Hero typing effect for subtitle
function initTypingEffect() {
    const subtitle = document.querySelector('.hero-subtitle');
    if (!subtitle) return;

    const texts = {
        cs: 'Edge AI zpracování, ANPR sledování, hlasový asistent a OBD diagnostika - vše v jednom systému. Ušetřete 70-93% oproti tradičním řešením.',
        en: 'Edge AI processing, ANPR surveillance, voice assistant, and OBD diagnostics - all in one system. Save 70-93% compared to traditional solutions.'
    };

    function typeText(text, element, speed = 50) {
        element.textContent = '';
        let i = 0;

        function type() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(type, speed);
            }
        }

        type();
    }

    // Start typing effect after a delay
    setTimeout(() => {
        typeText(texts[currentLanguage], subtitle, 30);
    }, 1000);
}

// Feature cards hover effects
function initFeatureEffects() {
    const featureCards = document.querySelectorAll('.feature-card');

    featureCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-10px) scale(1.02)';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0) scale(1)';
        });
    });
}

// Use case section animations
function initUseCaseAnimations() {
    const useCases = document.querySelectorAll('.use-case');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const image = entry.target.querySelector('.use-case-image img, .placeholder-image');
                const text = entry.target.querySelector('.use-case-text');

                if (image) {
                    image.style.animation = 'slideInRight 0.8s ease forwards';
                }
                if (text) {
                    text.style.animation = 'slideInLeft 0.8s ease forwards';
                }
            }
        });
    }, { threshold: 0.3 });

    useCases.forEach(useCase => {
        observer.observe(useCase);
    });
}

// Add slide animations to CSS dynamically
function addSlideAnimations() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInLeft {
            from {
                opacity: 0;
                transform: translateX(-50px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(50px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
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

        .nav-menu.mobile-active {
            display: flex;
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--surface);
            flex-direction: column;
            padding: var(--spacing-lg);
            box-shadow: var(--shadow-lg);
            border-radius: 0 0 var(--radius-lg) var(--radius-lg);
        }

        .pricing-card.selected {
            border-color: var(--accent);
            box-shadow: 0 0 30px rgba(16, 185, 129, 0.3);
        }

        @media (max-width: 768px) {
            .nav-menu {
                display: none;
            }
        }
    `;
    document.head.appendChild(style);
}

// CTA button interactions
function initCTAButtons() {
    const ctaButtons = document.querySelectorAll('.btn-primary, .cta-btn');

    ctaButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            // Add ripple effect
            const ripple = document.createElement('span');
            const rect = button.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;

            button.style.position = 'relative';
            button.style.overflow = 'hidden';
            button.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });

    // Add ripple animation
    const rippleStyle = document.createElement('style');
    rippleStyle.textContent = `
        @keyframes ripple {
            to {
                transform: scale(2);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(rippleStyle);
}

// Stats counter animation
function initStatsCounter() {
    const stats = document.querySelectorAll('.stat-number');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = entry.target;
                const text = target.textContent;
                const numbers = text.match(/\d+/g);

                if (numbers) {
                    const finalNumber = parseInt(numbers[0]);
                    animateCounter(target, finalNumber, text);
                }
            }
        });
    }, { threshold: 0.5 });

    stats.forEach(stat => {
        observer.observe(stat);
    });
}

function animateCounter(element, target, originalText) {
    let current = 0;
    const increment = target / 50;
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = originalText.replace(/\d+/, Math.floor(current));
    }, 40);
}

// Performance optimization - lazy load images
function initLazyLoading() {
    const images = document.querySelectorAll('img[loading="lazy"]');

    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src || img.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => {
            imageObserver.observe(img);
        });
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Load saved language preference
    const savedLanguage = localStorage.getItem('preferred-language');
    if (savedLanguage && savedLanguage !== currentLanguage) {
        switchLanguage(savedLanguage);
    }

    // Initialize all features
    initSmoothScrolling();
    initScrollAnimations();
    initNavbarEffects();
    initMobileMenu();
    initPricingCalculator();
    initTypingEffect();
    initFeatureEffects();
    initUseCaseAnimations();
    initCTAButtons();
    initStatsCounter();
    initLazyLoading();
    addSlideAnimations();

    // Add some loading effects
    document.body.classList.add('loaded');

    console.log('AI-SERVIS website initialized successfully');
});

// Add loading styles
const loadingStyle = document.createElement('style');
loadingStyle.textContent = `
    body:not(.loaded) {
        overflow: hidden;
    }

    body:not(.loaded) .hero {
        opacity: 0;
        transform: translateY(20px);
    }

    body.loaded .hero {
        opacity: 1;
        transform: translateY(0);
        transition: all 0.8s ease;
    }
`;
document.head.appendChild(loadingStyle);
