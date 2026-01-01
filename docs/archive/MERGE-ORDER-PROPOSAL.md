# PR Merge Order Proposal

**Date:** 2025-12-05  
**Status:** All PRs rebased onto latest main  
**Base:** `c33d50a` (latest main)

---

## Summary

All 6 open PRs have been successfully rebased onto the latest `main` branch. Conflicts have been resolved. Below is the recommended merge order based on dependencies, size, and risk.

---

## PR Status After Rebase

| PR # | Branch | Title | Status | Size | Conflicts Resolved |
|------|--------|-------|--------|------|-------------------|
| #38 | `fix/nodejs-cache-path` | fix(ci): correct Node.js cache path | ✅ MERGEABLE | Small | None |
| #39 | `refactor/ci-cd-workflows` | refactor: consolidate and enhance CI/CD workflows | ✅ MERGEABLE | Medium | None |
| #40 | `feat/web-features-journalists` | feat: add web features - journalists audio and monitoring | ✅ MERGEABLE | Medium | None |
| #41 | `refactor/android-build-cleanup` | refactor: simplify Android build configuration | ✅ MERGEABLE | Medium | None |
| #37 | `android-todo-implementation` | Android todo implementation | ✅ REBASED | Large | ✅ Resolved |
| #36 | `feature/journalists-audio-autoplay` | fix(ci): correct Node.js cache path | ✅ REBASED | Medium | ✅ Resolved |

---

## Recommended Merge Order

### Phase 1: Foundation & Infrastructure (Low Risk)

**1. PR #38 - `fix/nodejs-cache-path`** ⭐ **MERGE FIRST**
- **Priority:** HIGHEST
- **Reason:** Smallest, simplest fix. No dependencies. Safe to merge immediately.
- **Risk:** Very Low
- **Dependencies:** None
- **Estimated Time:** 5 minutes

**2. PR #39 - `refactor/ci-cd-workflows`**
- **Priority:** HIGH
- **Reason:** CI/CD infrastructure changes. Should be merged before other PRs that might depend on workflow changes.
- **Risk:** Low-Medium (affects all CI/CD)
- **Dependencies:** None (but affects future PRs)
- **Estimated Time:** 15 minutes

### Phase 2: Feature Additions (Medium Risk)

**3. PR #40 - `feat/web-features-journalists`**
- **Priority:** MEDIUM
- **Reason:** Web features. Independent of Android changes.
- **Risk:** Low
- **Dependencies:** None
- **Note:** PR #36 appears to be a duplicate/older version of this. Consider closing #36 after #40 merges.
- **Estimated Time:** 10 minutes

**4. PR #41 - `refactor/android-build-cleanup`**
- **Priority:** MEDIUM
- **Reason:** Android build simplification. Should merge before #37 to avoid conflicts.
- **Risk:** Medium (affects Android builds)
- **Dependencies:** None
- **Estimated Time:** 15 minutes

### Phase 3: Large Changes (Higher Risk, Requires Review)

**5. PR #37 - `android-todo-implementation`** ⚠️ **REQUIRES CAREFUL REVIEW**
- **Priority:** MEDIUM-HIGH
- **Reason:** Large PR with rename (ai-servis → mia). Contains 8 commits including:
  - Comprehensive BLE, API, and architecture improvements
  - Bug fixes
  - **Rename from ai-servis to mia** (215 files, 86 directories)
  - Namespace and workflow reference fixes
- **Risk:** HIGH (large changes, rename affects entire codebase)
- **Dependencies:** Should merge after #41 (Android build cleanup)
- **Conflicts Resolved:**
  - ✅ BLEManager.kt (Android 13+ compatibility)
  - ✅ BLEManagerTest.kt (test setup)
  - ✅ ANPRManager.kt (import conflicts)
  - ✅ Workflow files (accepted incoming)
  - ✅ README files (accepted incoming)
- **Estimated Time:** 30-45 minutes (review + merge)
- **Recommendation:** 
  - Request multiple reviewers
  - Test Android build thoroughly
  - Verify all package references updated
  - Check CI/CD workflows still work

**6. PR #36 - `feature/journalists-audio-autoplay`** ⚠️ **CONSIDER CLOSING**
- **Priority:** LOW (likely duplicate)
- **Reason:** Appears to be an older version of PR #40. Contains similar web features.
- **Risk:** Low (but redundant)
- **Dependencies:** None
- **Conflicts Resolved:**
  - ✅ Web i18n files (accepted incoming)
  - ✅ package.json (accepted incoming)
- **Recommendation:** 
  - **Review if it has unique changes not in #40**
  - **If duplicate, close this PR after #40 merges**
  - **If unique, merge after #40**
- **Estimated Time:** 5-10 minutes (if merging)

---

## Detailed Merge Sequence

```
main (c33d50a)
  │
  ├─→ PR #38: fix/nodejs-cache-path
  │     └─→ main + #38
  │
  ├─→ PR #39: refactor/ci-cd-workflows
  │     └─→ main + #38 + #39
  │
  ├─→ PR #40: feat/web-features-journalists
  │     └─→ main + #38 + #39 + #40
  │
  ├─→ PR #41: refactor/android-build-cleanup
  │     └─→ main + #38 + #39 + #40 + #41
  │
  ├─→ PR #37: android-todo-implementation (LARGE - RENAME)
  │     └─→ main + #38 + #39 + #40 + #41 + #37
  │
  └─→ PR #36: feature/journalists-audio-autoplay (REVIEW/CLOSE)
        └─→ main + #38 + #39 + #40 + #41 + #37 + #36 (if unique)
```

---

## Merge Strategy

### Option A: Sequential Merge (Recommended)
Merge one PR at a time, waiting for CI to pass before merging the next.

**Pros:**
- Easy to identify which PR causes issues
- Each PR can be tested independently
- Clear rollback point if something breaks

**Cons:**
- Slower (sequential CI runs)
- Each merge might trigger CI for dependent PRs

**Steps:**
1. Merge PR #38 → Wait for CI → Verify
2. Merge PR #39 → Wait for CI → Verify
3. Merge PR #40 → Wait for CI → Verify
4. Merge PR #41 → Wait for CI → Verify
5. **Review PR #37 carefully** → Merge → Wait for CI → Verify
6. Review PR #36 → Merge or Close

### Option B: Batch Merge (Faster, Higher Risk)
Merge PRs #38, #39, #40, #41 together, then review #37 separately.

**Pros:**
- Faster (parallel CI runs possible)
- Less context switching

**Cons:**
- Harder to identify which PR causes issues
- More complex rollback

**Steps:**
1. Merge PRs #38, #39, #40, #41 (in order, but can be faster)
2. Wait for all CI to pass
3. Review and merge PR #37
4. Review and merge/close PR #36

---

## Risk Assessment

### Low Risk PRs (Safe to merge quickly)
- ✅ PR #38: Small fix, no dependencies
- ✅ PR #40: Web features, isolated
- ✅ PR #41: Build cleanup, well-tested

### Medium Risk PRs (Require CI verification)
- ⚠️ PR #39: CI/CD changes affect all workflows
- ⚠️ PR #36: Potential duplicate, needs review

### High Risk PRs (Require thorough review)
- 🔴 PR #37: 
  - **Large changes** (8 commits, 215 files)
  - **Rename operation** (ai-servis → mia)
  - **Affects entire codebase**
  - **Requires:**
    - Multiple reviewers
    - Full Android build test
    - CI/CD workflow verification
    - Package reference verification
    - Documentation update verification

---

## Pre-Merge Checklist for PR #37

Before merging PR #37 (the rename), verify:

- [ ] All package references updated (`cz.aiservis.app` → `cz.mia.app`)
- [ ] All class names updated (`AIServisApplication` → `MIAApplication`)
- [ ] Conan package name updated (`ai-servis` → `mia`)
- [ ] Docker service names verified (note: these were NOT renamed, still `ai-servis-*`)
- [ ] All documentation updated
- [ ] CI/CD workflows still reference correct names
- [ ] Android build succeeds
- [ ] All tests pass
- [ ] No broken imports or references
- [ ] Repository URLs updated (if applicable)

---

## Post-Merge Actions

After merging PR #37:

1. **Update all dependent branches** that might reference old names
2. **Update documentation** that references the old name
3. **Notify team** about the rename
4. **Update CI/CD secrets** if they reference old names
5. **Update deployment scripts** if they reference old names

---

## Estimated Total Time

- **Phase 1 (PRs #38, #39):** 20 minutes
- **Phase 2 (PRs #40, #41):** 25 minutes
- **Phase 3 (PR #37 review + merge):** 45-60 minutes
- **Phase 4 (PR #36 review):** 10 minutes

**Total:** ~2 hours (including CI wait times and review)

---

## Recommendations

1. **Start with PR #38** - Quick win, no risk
2. **Merge PRs #39, #40, #41** - Can be done in parallel after #38
3. **Carefully review PR #37** - This is the big one. Consider:
   - Creating a staging branch to test the rename
   - Running full test suite
   - Verifying all references
4. **Review PR #36** - Likely duplicate of #40, consider closing
5. **Monitor CI** - After each merge, ensure CI passes before next merge

---

## Notes

- All PRs have been rebased and are ready to merge
- Conflicts have been resolved
- PR #37 contains the "mia" rename - this is a significant change
- PR #36 appears to be a duplicate of PR #40 - verify before merging
- Docker service names were NOT renamed (still `ai-servis-*`) - this is intentional

---

## Next Steps

1. ✅ All PRs rebased - **DONE**
2. ⏳ Review this merge order proposal
3. ⏳ Start merging in recommended order
4. ⏳ Monitor CI after each merge
5. ⏳ Verify PR #36 is duplicate before merging/closing
