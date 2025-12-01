(function () {
  const loader = window.I18nLoader;
  const basePath = normalizeBasePath(
    document.documentElement.getAttribute("data-base-path") || "/"
  );

  function normalizeBasePath(path) {
    if (!path) return "/";
    if (!path.startsWith("/")) {
      path = `/${path}`;
    }
    return path.endsWith("/") ? path : `${path}/`;
  }

  function withBasePath(href) {
    if (!href) {
      return href;
    }
    if (href.startsWith("#")) {
      return href;
    }
    if (/^(https?:)?\/\//i.test(href) || href.startsWith("mailto:")) {
      return href;
    }
    if (href.startsWith("/")) {
      return `${basePath}${href.slice(1)}`;
    }
    return href;
  }

  function updateLanguageButtons(lang) {
    const buttons = document.querySelectorAll("[data-lang-switch]");
    buttons.forEach((button) => {
      const isActive = button.dataset.langSwitch === lang;
      button.classList.toggle("lang-switcher__button--active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
    document.documentElement.setAttribute("lang", lang);
  }

  function enhanceLinks() {
    document.querySelectorAll("a[href]").forEach((anchor) => {
      const href = anchor.getAttribute("href");
      const normalized = withBasePath(href);
      if (normalized !== href) {
        anchor.setAttribute("href", normalized);
      }
    });
  }

  function initLanguageSwitcher() {
    document
      .querySelectorAll("[data-lang-switch]")
      .forEach((button) =>
        button.addEventListener("click", () => {
          const targetLang = button.dataset.langSwitch;
          loader.setLanguage(targetLang);
          updateLanguageButtons(targetLang);
        })
      );

    loader.onLanguageChange(updateLanguageButtons);
  }

  function init() {
    enhanceLinks();
    loader.translateDom();
    initLanguageSwitcher();
    updateLanguageButtons(loader.getLanguage());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
