(function (global) {
  let source = global.__I18N__ || {};
  let currentLang = global.__DEFAULT_LANGUAGE__ || "cs";
  const listeners = new Set();

  const isObject = (value) =>
    value !== null && typeof value === "object" && !Array.isArray(value);

  const getValue = (path) => {
    if (!path) {
      return undefined;
    }

    const segments = path.split(".");
    let pointer = source;

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

  const setNestedValue = (target, path, value) => {
    let pointer = target;
    for (let index = 0; index < path.length - 1; index += 1) {
      const segment = path[index];
      pointer[segment] = pointer[segment] || {};
      pointer = pointer[segment];
    }
    pointer[path[path.length - 1]] = value;
  };

  const parseScalar = (value) =>
    value.trim().replace(/^['"]|['"]$/g, "");

  const getValueFrom = (root, path) => {
    let pointer = root;
    for (const segment of path) {
      if (!isObject(pointer)) {
        return undefined;
      }
      pointer = pointer[segment];
    }
    return pointer;
  };

  const parseSimpleYaml = (yamlText) => {
    const result = {};
    const pathStack = [];

    yamlText.split(/\r?\n/).forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) {
        return;
      }

      const indent = line.length - line.trimStart().length;
      const depth = Math.floor(indent / 2);
      const separator = trimmed.indexOf(":");
      if (separator === -1) {
        return;
      }

      const key = trimmed.slice(0, separator).trim();
      const rawValue = trimmed.slice(separator + 1).trim();
      pathStack.length = depth;
      pathStack[depth] = key;

      if (rawValue) {
        setNestedValue(
          result,
          pathStack.slice(0, depth + 1),
          parseScalar(rawValue)
        );
      } else {
        const currentPath = pathStack.slice(0, depth + 1);
        setNestedValue(result, currentPath, getValueFrom(result, currentPath) || {});
      }
    });

    return result;
  };

  const translateElement = (element) => {
    const path = element.getAttribute("data-i18n-path") ||
      element.getAttribute("data-i18n");
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
      ? scope.querySelectorAll("[data-i18n-path], [data-i18n]")
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

  const init = async (options = {}) => {
    currentLang = options.defaultLanguage || currentLang;
    global.__DEFAULT_LANGUAGE__ = currentLang;

    if (options.i18nDataPath) {
      const response = await fetch(options.i18nDataPath);
      if (!response.ok) {
        throw new Error(`Failed to load ${options.i18nDataPath}: ${response.status}`);
      }
      source = parseSimpleYaml(await response.text());
      global.__I18N__ = source;
    } else if (global.__I18N__) {
      source = global.__I18N__;
    }

    translateDom();
    listeners.forEach((listener) => {
      try {
        listener(currentLang);
      } catch (error) {
        console.warn("i18n listener failed", error);
      }
    });
  };

  global.I18nLoader = {
    init,
    getLanguage: () => currentLang,
    setLanguage,
    translateDom,
    translateElement,
    getValue,
    onLanguageChange,
  };
})(window);
