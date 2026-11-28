# 0028. The app has an SSH terminal to the Pi, separate from the update key

- Status: Proposed
- Date: 2026-11-27
- Requirements: REQ-AND-029

## Context
Looking at the Pi in the car (logs, `systemctl`, a stuck unit) needs a shell. Until now that meant Termux or another
SSH app on the phone, set up by hand, with its own keys and host pins. The app already speaks SSH (sshj, ADR-0023,
ADR-0025), but its two keys are deliberately not shells: the update key runs only `mia-apply-update` through the
`mia-update` user, and the onboarding key only `mia-enroll`. ADR-0023 says a stolen phone key must not become an
interactive root shell.

## Decision
- **More > Terminal** opens an interactive shell: sshj with an `xterm-256color` PTY sized to the screen and kept in
  step on resize, `LANG=C.UTF-8`, a 15 s keepalive. The session lives in the view model, so it survives tab switches
  and rotation, and ends on Disconnect, when the shell exits or when the app process ends.
- **It signs in as an ordinary login user** (default `mia`), never `mia-update` or `mia-enroll`, with either the
  user's password or a **third key**, the terminal key: an EC P-256 pair made on first use, sealed by its own
  Android Keystore AES key (`mia_terminal_wrap`, file wrap on API 22) under `noBackupFilesDir/terminal`. The
  update key is never offered for a login. A password is used for one sign-in and never stored.
- **The terminal key is authorised only by someone who can already sign in**: the user copies the public line into
  `~/.ssh/authorized_keys`, or, signed in with the password, taps *Add phone key*, which appends it on a separate
  exec channel (nothing is typed into the running shell). The API cannot add it.
- **Host keys:** ssh-ed25519 only, as in onboarding (REQ-ONB-008). The first key seen for `host:port` is pinned in
  `terminal/known_hosts` and its fingerprint shown in the terminal; a different key later is refused with both
  fingerprints until the user forgets the pin. A Pi that finished the onboarding wizard is pinned from the start to
  the fingerprint the auth server vouched for.
- **The emulator is our own** (`TerminalEmulator.kt`, about 500 lines of Kotlin, no native code): the VT100/xterm
  subset that bash, `less`, `top`, `nano`, `vim` and `systemctl` use, with 2000 lines of scrollback. Termux's
  emulator is tied to a local process through JNI, and the Compose terminal libraries need newer Kotlin than the
  1.9.22 the app pins.

## Consequences
- The terminal key is as strong as the account it is added to: on the stock Pi image `mia` has sudo, so the key is
  root there, like the update key (ADR-0023), but only after the owner adds it, and it can be removed with one line
  in `authorized_keys`. A stolen, unlocked phone with that key is a shell on the Pi.
- The emulator does not reflow lines on resize, draws wide (CJK, emoji) characters as one cell and has no mouse
  reporting; full-screen programs still work because they redraw on SIGWINCH.
- There is no copy by selection: *Copy* takes the visible screen, *Paste* sends the clipboard (bracketed when the
  shell asks for it).

## Sources
- `apps/android/app/src/main/java/cz/mia/app/core/terminal/`
- `apps/android/app/src/main/java/cz/mia/app/features/terminal/TerminalViewModel.kt`
- `apps/android/app/src/main/java/cz/mia/app/ui/screens/TerminalScreen.kt`
- ADR-0023 (update key), ADR-0025 (onboarding host-key pin)
