(function (global) {
  const SOURCE = global.__I18N__ || {};
  let currentLang = global.__DEFAULT_LANGUAGE__ || "cs";
  const listeners = new Set();

  const isObject = (value) =>
    value !== null && typeof value === "object" && !Array.isArray(value);

  const getValue = (path) => {
    if (!path) {
      return undefined;
    }

    const segments = path.split(".");
    let pointer = SOURCE;

    for (const segment of segments) {
      if (!isObject(pointer) && !Array.isArray(pointer)) {
        return undefined;
      }
      pointer = pointer?.[segment];
      if (pointer === undefined || pointer === null) {
        return undefined;
      }
    }

    return pointer;
  };

  const translateElement = (element) => {
    const path = element.getAttribute("data-i18n-path");
    if (!path) {
      return;
    }

    const value = getValue(path);
    if (value === undefined) {
      return;
    }

    if (isObject(value)) {
      const localized = value[currentLang] ?? value.en ?? value.cs;
      if (typeof localized === "string") {
        element.textContent = localized;
      }
    } else if (typeof value === "string") {
      element.textContent = value;
    }
  };

  const translateDom = (root = global.document) => {
    const scope = root instanceof Element ? root : root.documentElement || root;
    const elements = scope.querySelectorAll
      ? scope.querySelectorAll("[data-i18n-path]")
      : [];
    elements.forEach(translateElement);
  };

  const setLanguage = (lang) => {
    if (!lang || lang === currentLang) {
      return;
    }
    currentLang = lang;
    translateDom();
    listeners.forEach((listener) => {
      try {
        listener(currentLang);
      } catch (error) {
        console.warn("i18n listener failed", error);
      }
    });
  };

  const onLanguageChange = (listener) => {
    if (typeof listener === "function") {
      listeners.add(listener);
      return () => listeners.delete(listener);
    }
    return () => undefined;
  };

  global.I18nLoader = {
    getLanguage: () => currentLang,
    setLanguage,
    translateDom,
    translateElement,
    getValue,
    onLanguageChange,
  };
})(window);
