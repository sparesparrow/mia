#!/bin/bash
# Bring the Pi's MIA source checkout to a deploy ref (REQ-DEP-008). Step 1 of deploy-production-rpi.sh, run as root.
#
#   mia-update-checkout.sh <checkout> [ref]       ref: $MIA_DEPLOY_REF, default origin/main
#
# - git runs as the checkout's owner. As root, git refuses a repository another user owns ("detected dubious
#   ownership"), and objects written by root would break the owner's own git commands later.
# - It fetches origin (skipped with MIA_DEPLOY_SKIP_FETCH=1) and checks the ref's commit out detached: a deploy pins a
#   commit and never creates a merge commit on the Pi.
# - A local edit, or an untracked file that the target commit tracks, is dropped only when its content already equals
#   the target's (a fix copied in by hand before it was merged). Anything else stops the deploy and lists the paths,
#   so local work is never lost. Untracked files the target does not track, such as run-time data, are not touched.
#
# The last line on stdout is the deployed commit.

set -euo pipefail

CHECKOUT="${1:?usage: mia-update-checkout.sh <checkout> [ref]}"
REF="${2:-${MIA_DEPLOY_REF:-origin/main}}"

if [[ ! -d "$CHECKOUT/.git" ]]; then
    echo "mia-update-checkout: $CHECKOUT is not a git checkout" >&2
    exit 1
fi

OWNER="$(stat -c %U "$CHECKOUT/.git")"

as_owner() {
    if [[ "$OWNER" == "$(id -un)" ]]; then
        "$@"
    elif command -v runuser >/dev/null 2>&1; then
        runuser -u "$OWNER" -- "$@"
    else
        sudo -u "$OWNER" -H -- "$@"
    fi
}

g() { as_owner git -C "$CHECKOUT" "$@"; }

if [[ "${MIA_DEPLOY_SKIP_FETCH:-0}" != "1" ]]; then
    echo "Fetching origin as $OWNER..." >&2
    g fetch --prune --quiet origin
fi

if ! TARGET="$(g rev-parse --verify --quiet "${REF}^{commit}")"; then
    echo "mia-update-checkout: unknown ref '$REF'" >&2
    exit 1
fi

# The blob id a path has in the target commit, or nothing when the target does not track it.
target_blob() { g rev-parse --verify --quiet "$TARGET:$1" 2>/dev/null || true; }
# The blob id the path's working-tree content would get, or nothing when the file is absent.
local_blob() { if [[ -e "$CHECKOUT/$1" || -L "$CHECKOUT/$1" ]]; then g hash-object -- "$1"; fi; }

conflicts=()
same_tracked=()
same_untracked=()

# Tracked paths that differ from HEAD, staged or not (modified, deleted or newly added).
while IFS= read -r -d '' path; do
    if [[ "$(local_blob "$path")" == "$(target_blob "$path")" ]]; then
        same_tracked+=("$path")
    else
        conflicts+=("$path")
    fi
done < <(g diff --name-only -z HEAD)

# Untracked files the target commit would write over.
while IFS= read -r -d '' path; do
    blob="$(target_blob "$path")"
    [[ -z "$blob" ]] && continue
    if [[ "$(local_blob "$path")" == "$blob" ]]; then
        same_untracked+=("$path")
    else
        conflicts+=("$path")
    fi
done < <(g ls-files --others --exclude-standard -z)

if [[ ${#conflicts[@]} -gt 0 ]]; then
    echo "mia-update-checkout: local changes in $CHECKOUT differ from $REF ($TARGET); nothing was changed:" >&2
    printf '  %s\n' "${conflicts[@]}" >&2
    echo "Commit or move them, then deploy again." >&2
    exit 1
fi

for path in "${same_tracked[@]}"; do
    if g cat-file -e "HEAD:$path" 2>/dev/null; then
        g checkout --quiet HEAD -- "$path"
    else
        g rm --quiet --force -- "$path"
    fi
done
for path in "${same_untracked[@]}"; do
    as_owner rm -f -- "$CHECKOUT/$path"
done
if [[ $(( ${#same_tracked[@]} + ${#same_untracked[@]} )) -gt 0 ]]; then
    echo "Dropped $(( ${#same_tracked[@]} + ${#same_untracked[@]} )) local file(s) whose content is already in $REF." >&2
fi

PREVIOUS="$(g rev-parse HEAD)"
g checkout --quiet --detach "$TARGET"
echo "Checkout: $PREVIOUS -> $TARGET ($REF)" >&2
echo "$TARGET"
