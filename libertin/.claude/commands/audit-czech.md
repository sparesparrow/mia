Audit Czech string hygiene across the codebase.

Check for:
1. Hardcoded Czech strings outside packages/i18n/locales.json — grep for Czech
   characters (á,č,ď,é,ě,í,ň,ó,ř,š,ť,ú,ů,ý,ž) in .tsx/.ts files outside i18n package
2. Forbidden typos — flag any occurrence:
   - "Zapomenuté" (without "heslo" following)
   - incorrect "Máte" / "svoji" usage
3. Hardcoded PII — real email addresses or phone numbers (+420…) outside test fixtures;
   must be {email}/{phone} interpolation keys
4. Raw hex colors in component files — must use CSS vars (var(--color-*)) or theme tokens

Report file:line for each violation. Exit 1 if any violations found.
