// MIA site interactions. The only thing that starts by itself is the soundtrack, and only until the visitor
// switches it off.
(() => {
  const init = () => {
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener('click', (event) => {
        const target = document.querySelector(anchor.getAttribute('href'));
        if (!target) return;
        event.preventDefault();
        const headerOffset = 100;
        const top = target.getBoundingClientRect().top + window.scrollY - headerOffset;
        window.scrollTo({ top, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      });
    });

    // Soundtrack: starts by itself unless the visitor switched it off before (stored in localStorage).
    // Browsers block sound before the first interaction, so a rejected start waits for the first click or
    // tap. Key presses never start it: a keyboard or screen-reader user's first Tab must not talk over their
    // screen reader (WCAG 1.4.2); they use the button. The 🎵/🔊 button always pauses and resumes. The voice
    // guides take priority: touching a crew card or the widget pauses the music and never starts it.
    const audio = document.getElementById('background-music');
    const toggle = document.getElementById('audio-toggle');
    if (audio && toggle) {
      const STORE_KEY = 'mia-music';
      const remember = (value) => {
        try {
          if (value) localStorage.setItem(STORE_KEY, value);
          else localStorage.removeItem(STORE_KEY);
        } catch (error) { /* storage unavailable: the choice lasts for this page view */ }
      };
      const switchedOff = () => {
        try { return localStorage.getItem(STORE_KEY) === 'off'; } catch (error) { return false; }
      };
      const isCrew = (target) => target instanceof Element && target.closest('.crew-card, #crew-widget');
      const GESTURES = ['pointerdown'];

      audio.volume = 0.25;
      const updateAudioButton = () => {
        const playing = !audio.paused;
        toggle.textContent = playing ? '🔊' : '🎵';
        toggle.title = playing ? 'Pause soundtrack' : 'Play soundtrack';
        toggle.setAttribute('aria-pressed', String(playing));
        toggle.classList.toggle('playing', playing);
      };
      const disarm = () => GESTURES.forEach((type) => document.removeEventListener(type, onGesture, true));
      async function onGesture(event) {
        if (event.target instanceof Element && event.target.closest('#audio-toggle')) return;
        if (isCrew(event.target)) return;
        disarm();
        try {
          await audio.play();
        } catch (error) {
          arm();
        }
      }
      const arm = () => GESTURES.forEach((type) => document.addEventListener(type, onGesture, true));

      toggle.addEventListener('click', async () => {
        disarm();
        try {
          if (audio.paused) {
            remember(null);
            await audio.play();
          } else {
            remember('off');
            audio.pause();
          }
        } catch (error) {
          toggle.title = 'Audio playback is unavailable in this browser';
        }
        updateAudioButton();
      });
      document.addEventListener('pointerdown', (event) => {
        if (isCrew(event.target)) {
          disarm();
          audio.pause();
        }
      }, true);
      audio.addEventListener('play', updateAudioButton);
      audio.addEventListener('pause', updateAudioButton);
      updateAudioButton();

      if (!switchedOff()) {
        audio.play().catch(arm);
      }
    }

    document.querySelectorAll('.price-card').forEach((card) => {
      card.addEventListener('click', () => {
        document.querySelectorAll('.price-card').forEach((item) => item.classList.remove('selected'));
        card.classList.add('selected');
      });
    });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
