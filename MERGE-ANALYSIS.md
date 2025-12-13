# Merge Analysis: android-todo-implementation → main

**Date:** 2025-12-05  
**Analysis:** Rename commit and branch divergence

---

## Summary

The `android-todo-implementation` branch contains the "mia" rename (commit `bea45ba`) but has significantly diverged from `main`. A merge would require careful conflict resolution.

---

## Branch Statistics

### Commits
- **Common ancestor:** `32fa345c` (Dec 5, 2025)
- **main ahead:** 23 commits
- **android-todo-implementation ahead:** 8 commits (including rename)

### File Changes
- **Total files changed:** 231
- **Insertions:** +1,779
- **Deletions:** -3,517
- **Net change:** -1,738 lines

### Key Commits on android-todo-implementation
1. `fcc457a` - Fix failing checks: Update namespace and workflow references
2. `bea45ba` - **Rename repository and product from ai-servis to mia** ⭐
3. `c2d5ebe` - Fix: Update BLE write characteristic logic for Android 13+
4. `7c0e576` - fix(android): Implement critical bug fixes from TODO.md
5. `5667d06` - fix(android): resolve deprecated APIs and logic errors causing test failures
6. `fd40b22` - fix(test): remove obsolete onCleared test in BleDevicesViewModelTest
7. `2165c24` - android app bugfixing updates
8. `458be22` - feat(android): implement comprehensive BLE, API, and architecture improvements

### Key Commits on main (since divergence)
1. `c33d50a` - Merge pull request #32 (Raspberry Pi C++ implementation)
2. `8707ebb` - feat: implement automatic audio play for journalists web page
3. `e73d398` - feat: add web page generation and deployment workflow
4. `79fe182` - fix(android): resolve Kotlin compilation errors
5. `b7bc4d4` - feat(android): implement complete vehicle telematics system
6. Plus 18 more commits...

---

## Rename Details (bea45ba)

The rename commit changes:
- Package: `cz.aiservis.app` → `cz.mia.app`
- Application class: `AIServisApplication` → `MIAApplication`
- Conan class: `AiServisConan` → `MIAConan`
- Conan name: `"ai-servis"` → `"mia"`
- Repository URLs: `sparesparrow/ai-servis` → `sparesparrow/mia`
- Environment variables: `AI_SERVIS_*` → `MIA_*`
- **Note:** Docker service names in `docker-compose.yml` were NOT renamed (still `ai-servis-*`)

**Files affected:** 215 files modified, 86 directories renamed

---

## Merge Strategy Options

### Option 1: Merge android-todo-implementation → main (Recommended)
**Pros:**
- Preserves all work from both branches
- Keeps rename consistent across codebase
- Maintains commit history

**Cons:**
- Will require resolving 231 file conflicts
- Large merge commit
- May break existing PRs based on old naming

**Steps:**
```bash
git checkout main
git merge android-todo-implementation
# Resolve conflicts (many expected)
git commit -m "Merge android-todo-implementation: Rename ai-servis to mia"
```

### Option 2: Rebase android-todo-implementation onto main
**Pros:**
- Cleaner history
- Easier to review changes

**Cons:**
- Rewrites history (force push required)
- More complex conflict resolution
- May break existing PRs

**Steps:**
```bash
git checkout android-todo-implementation
git rebase main
# Resolve conflicts for each commit
git push --force-with-lease
```

### Option 3: Cherry-pick rename commit to main
**Pros:**
- Minimal change
- Can be done incrementally

**Cons:**
- Loses other fixes from android-todo-implementation
- May create duplicate commits
- Doesn't solve the divergence issue

**Steps:**
```bash
git checkout main
git cherry-pick bea45ba
# Resolve conflicts
git commit --amend
```

### Option 4: Create new branch from main and re-apply rename
**Pros:**
- Clean slate
- Can apply rename incrementally

**Cons:**
- Loses commit history
- More work required

---

## Conflict Areas (Expected)

Based on file changes, conflicts likely in:

1. **Android files:**
   - `android/app/build.gradle` (namespace, applicationId)
   - `android/app/src/main/AndroidManifest.xml` (application name)
   - All Kotlin files in `cz.aiservis.app` vs `cz.mia.app` packages

2. **Configuration files:**
   - `conanfile.py` (class name, package name)
   - `.github/workflows/*.yml` (repository references)
   - `docker-compose.yml` (service names - though not renamed)

3. **Documentation:**
   - All `.md` files with "ai-servis" references
   - README files
   - Architecture docs

4. **Web files:**
   - `web/package.json` (different versions on each branch)
   - Journalists web page files (deleted on android-todo-implementation)

---

## Recommendation

**Recommended: Option 1 (Merge) with careful conflict resolution**

1. **Create a merge branch:**
   ```bash
   git checkout main
   git checkout -b merge/mia-rename
   git merge android-todo-implementation
   ```

2. **Resolve conflicts systematically:**
   - Start with Android package rename (`cz.aiservis.app` → `cz.mia.app`)
   - Then Conan configuration
   - Then documentation
   - Finally, web files

3. **Test thoroughly:**
   - Android build
   - Docker compose services
   - CI/CD workflows

4. **Create PR for review:**
   - Large PR, but necessary for consistency
   - Request multiple reviewers
   - Test on staging environment

---

## Alternative: Keep Branches Separate

If the merge is too complex, consider:
- Keep `android-todo-implementation` as the "mia" branch
- Gradually migrate features from `main` to `android-todo-implementation`
- Eventually make `android-todo-implementation` the new `main`

**This approach:**
- Avoids large merge conflicts
- Allows incremental migration
- But creates maintenance overhead

---

## Next Steps

1. **Decision needed:** Choose merge strategy
2. **If merging:** Create merge branch and start conflict resolution
3. **If keeping separate:** Document the branch strategy
4. **Update CURSOR-PLAN.md:** Already fixed for `android-todo-implementation` branch

---

## Notes

- The rename commit (`bea45ba`) is well-structured and comprehensive
- Docker service names were intentionally NOT renamed (still `ai-servis-*`)
- `CURSOR-PLAN.md` has been updated to reflect correct service names
- Both branches have valuable work that should be preserved
