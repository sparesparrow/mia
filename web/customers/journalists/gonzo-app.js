// MIA site interactions: deliberate, user-triggered behaviour only.
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

    const audio = document.getElementById('background-music');
    const toggle = document.getElementById('audio-toggle');
    if (audio && toggle) {
      audio.volume = 0.25;
      const updateAudioButton = () => {
        const playing = !audio.paused;
        toggle.textContent = playing ? '🔊' : '🎵';
        toggle.title = playing ? 'Pause soundtrack' : 'Play soundtrack';
        toggle.setAttribute('aria-pressed', String(playing));
        toggle.classList.toggle('playing', playing);
      };
      toggle.addEventListener('click', async () => {
        try {
          if (audio.paused) await audio.play();
          else audio.pause();
        } catch (error) {
          toggle.title = 'Audio playback is unavailable in this browser';
        }
        updateAudioButton();
      });
      audio.addEventListener('play', updateAudioButton);
      audio.addEventListener('pause', updateAudioButton);
      updateAudioButton();
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
