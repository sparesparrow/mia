// Fails when the page scrolls sideways at the current viewport.
Cypress.Commands.add('assertNoHorizontalOverflow', () => {
    cy.document().then((doc) => {
        const root = doc.documentElement;
        expect(root.scrollWidth, 'document width').to.be.at.most(root.clientWidth + 1);
    });
});

// Fetches every same-origin href or src on the page that is not an in-page anchor and expects a 200.
Cypress.Commands.add('assertLocalLinksResolve', (selector = 'a[href], link[href], img[src], script[src]') => {
    cy.location('origin').then((origin) => {
        cy.get(selector).then(($els) => {
            const urls = [...new Set($els.toArray()
                .map((el) => el.href || el.src)
                .filter((url) => url && url.startsWith(origin) && !url.includes('#'))
                // MkDocs is built by a separate job and is not part of the local preview.
                .filter((url) => !new URL(url).pathname.includes('/docs/')))];
            urls.forEach((url) => {
                cy.request({ url, failOnStatusCode: false }).then((res) => expect(res.status, url).to.eq(200));
            });
        });
    });
});

// WCAG 2.2 SC 1.4.3 (AA) text contrast for text over solid backgrounds: 4.5:1, or 3:1 for large text
// (24px, or 18.66px bold). Text over a gradient or an image, and gradient-filled text, is skipped:
// its contrast depends on where the glyphs sit, so it is judged by eye. Element and ancestor opacity is
// folded into the text colour. Fails with one line per offending element style.
Cypress.Commands.add('assertTextContrast', () => {
    cy.window().then((win) => {
        const parse = (c) => {
            const m = /rgba?\(([^)]+)\)/.exec(c || '');
            if (!m) {
                return null;
            }
            const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
            return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
        };
        const channel = (v) => {
            const s = v / 255;
            return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
        };
        const lum = (c) => 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
        const over = (fg, bg) => ({
            r: fg.r * fg.a + bg.r * (1 - fg.a),
            g: fg.g * fg.a + bg.g * (1 - fg.a),
            b: fg.b * fg.a + bg.b * (1 - fg.a),
            a: 1
        });
        const background = (el) => {
            const layers = [];
            for (let e = el; e; e = e.parentElement) {
                const cs = win.getComputedStyle(e);
                if (cs.backgroundImage !== 'none') {
                    return null;
                }
                const c = parse(cs.backgroundColor);
                if (c && c.a > 0) {
                    layers.push(c);
                    if (c.a >= 1) {
                        break;
                    }
                }
            }
            return layers.reverse().reduce((bg, layer) => over(layer, bg), { r: 255, g: 255, b: 255, a: 1 });
        };
        const opacity = (el) => {
            let o = 1;
            for (let e = el; e; e = e.parentElement) {
                o *= Number(win.getComputedStyle(e).opacity);
            }
            return o;
        };
        const failures = new Map();
        const walker = win.document.createTreeWalker(win.document.body, win.NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
            const node = walker.currentNode;
            const el = node.parentElement;
            if (!node.textContent.trim() || !el || el.closest('script, style, noscript, .skip-link')) {
                continue;
            }
            const cs = win.getComputedStyle(el);
            const box = el.getBoundingClientRect();
            if (box.width === 0 || box.height === 0 || cs.visibility === 'hidden'
                || /transparent|rgba\(0, 0, 0, 0\)/.test(cs.webkitTextFillColor || '')) {
                continue;
            }
            const bg = background(el);
            const fg = parse(cs.color);
            const alpha = opacity(el);
            if (!bg || !fg || alpha === 0) {
                continue;
            }
            const text = over({ ...fg, a: fg.a * alpha }, bg);
            const [hi, lo] = [lum(text), lum(bg)].sort((x, y) => y - x);
            const ratio = (hi + 0.05) / (lo + 0.05);
            const size = parseFloat(cs.fontSize);
            const large = size >= 24 || (Number(cs.fontWeight) >= 700 && size >= 18.66);
            const needed = large ? 3 : 4.5;
            if (ratio < needed) {
                const cls = typeof el.className === 'string' && el.className.trim()
                    ? `.${el.className.trim().split(/\s+/).join('.')}` : '';
                const key = `${el.tagName.toLowerCase()}${cls} ${cs.color} on rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, `
                    + `${Math.round(bg.b)}) ${ratio.toFixed(2)} < ${needed} ("${node.textContent.trim().slice(0, 30)}")`;
                failures.set(key, (failures.get(key) || 0) + 1);
            }
        }
        const lines = [...failures].map(([key, n]) => `${n}x ${key}`);
        expect(lines, `text below WCAG AA contrast on ${win.location.pathname}`).to.deep.equal([]);
    });
});
