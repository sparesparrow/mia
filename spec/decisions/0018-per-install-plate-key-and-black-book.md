# 0018. Plate hashes use a per-install key; the black book outlives retention

- Status: Proposed
- Date: 2026-10-25
- Requirements: REQ-AND-004, REQ-AND-011, REQ-AND-020, REQ-AND-021

## Context
The Android app reads number plates with the phone's camera (REQ-AND-004) and stores each sighting as an
HMAC-SHA256 of the plate. Until now the HMAC key was the constant `"mia-anpr-secret"` in `ANPRManager.kt`. A
plate has few possible values, so anyone with the source and the database could hash every plate and reverse
the stored hashes. The hash protected nothing.

The owner also asked for a black book: plates the driver wants to be told about. They also asked for an alert
when the same car keeps turning up. Both need hashes that stay comparable on this phone: the camera's
reading and a typed plate must produce the same hash. Retention (2 days by default, 1 to 90 days) deletes
sightings. A black book that retention emptied would be useless.

Android Keystore can hold an HMAC key that never leaves secure hardware, but only from API 23. The app's
`minSdk` is 22.

## Decision
- **Key.** Each install makes 32 random bytes (`SecureRandom`) on first use and keeps them in the app's
  no-backup files (`Context.noBackupFilesDir`, `PlateKeyStore`). The app already sets `allowBackup="false"`.
  The key is never logged, exported or sent. A key file that is missing or the wrong size is replaced with a
  new key.
- **One hashing path.** `PlateIdentity` hashes both camera readings and typed plates, after the same
  normalisation. Normalisation removes spaces and dashes, makes letters upper case, and turns O into 0 and
  B into 8.
- **Old sightings are deleted.** Database version 2 deletes the version 1 `anpr_events`. They were hashed with
  the public constant, so they could be reversed, and they would never match a new hash.
- **Black book.** A `watchlist` table holds `(plateHash, label, addedAt)`. No clear plate is stored. Entries stay
  until the user removes them; retention does not apply, by the user's choice.
- **Alerts stay on the phone.** A black-book hit and a repeated plate raise a notification and speech only. They
  are not published over MQTT, and labels never leave the phone.
- **Not the Keystore yet.** The key is a file, not a Keystore key, while `minSdk` is 22. Raising `minSdk` to 23
  and moving the key into the Keystore is a later decision.

## Consequences
- A stored hash means nothing without this phone's key file, which is not in backups or exports.
- Reinstalling the app, clearing its data or a damaged key file makes a new key. The black book and recent
  sightings then no longer match; the user has to add the plates again.
- O/0 and B/8 hash alike, so two plates that differ only there match each other. OCR confuses those characters,
  so the merge is wanted, and the false matches it causes are accepted.
- The key file is readable by anyone who can read the app's private storage (a rooted phone, a forensic copy).
  The Keystore would close that gap from API 23.
- The black book holds personal data that retention does not remove. The DPIA (#137) must cover it, its labels
  and the repeated-sighting alert.
- Upgrading from version 1 loses at most the retention period of plate sightings; telemetry, alerts, clips and
  audit records are kept.

## Sources
`apps/android/app/src/main/java/cz/mia/app/core/security/PlateKeyStore.kt`, `PlateIdentity.kt`,
`apps/android/app/src/main/java/cz/mia/app/data/db/AppDatabase.kt` (`MIGRATION_1_2`),
`apps/android/app/src/main/java/cz/mia/app/core/anpr/`, `docs/privacy/dpia-template.md`.
