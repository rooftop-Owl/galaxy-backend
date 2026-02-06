# Git Hooks

This directory contains git hooks that enforce code quality, security, and governance for the astraeus repository.

## Installation

Hooks are automatically installed when you clone the repository. The git configuration is set to use this directory:

```bash
git config core.hooksPath .githooks
```

To verify hooks are installed:

```bash
git config core.hooksPath
# Should output: .githooks
```

## Available Hooks
## Tiered Validation System (Issue #88)

The pre-commit hook uses a **3-tier validation system** to reduce friction on housekeeping commits while maintaining full validation for feature work.

### Tier Classification

| Branch Pattern | Tier | Validation Level |
|----------------|------|------------------|
| `chore/*`, `docs/*`, `style/*` | **Housekeeping** | Security + conditional only |
| `feat/*`, `fix/*`, `refactor/*`, `perf/*`, `test/*` | **Feature** | Full validation |
| `release/*`, `hotfix/*` | **Feature** | Full validation |
| Other patterns | **Feature** (default) | Full validation |

### What Runs in Each Tier

**Tier 1 - Always Run (All Branches)**
- ✅ Session/Branch identity validation
- ✅ Secrets detection
- ✅ Large file detection (>5MB)
- ✅ Root directory organization
- ✅ Conditional checks (CoC, VERSION, docs/, JOURNAL.md)

**Tier 2 - Feature Branches Only**
- ✅ Fidelity validation (naming conventions)
- ✅ Changelog fragment check
- ✅ Command metadata validation
- ✅ Agent housing protocol validation
- ✅ Documentation sync check

**Housekeeping Branch Behavior**
On `chore/*`, `docs/*`, `style/*` branches:
- Session ID warning is **quiet** (blue info instead of yellow warning)
- Tier 2 checks show "ℹ️  [Check] skipped (housekeeping branch)"
- All security checks still run (no bypass)

### Examples

**Chore branch (minimal checks):**
```bash
git checkout -b chore/cleanup
echo "cleanup" >> temp.txt
git add temp.txt
git commit -m "chore: cleanup temp files"
# ✅ Steps 1-4 run (security)
# ℹ️  Steps 5, 6, 11, 14, 16 skipped
# ℹ️  Session ID warning is quiet
```

**Feature branch (full checks):**
```bash
git checkout -b feat/new-feature
# ... make changes ...
git commit -m "feat: add feature"
# ✅ All 14 steps run normally
# ⚠️  Full Session ID warning if manual commit
```

**Main branch (still blocked):**
```bash
git checkout main
echo "change" >> README.md
git commit -m "fix: direct to main"
# ❌ Blocked by session-branch-validator.sh
```

**Merge to main (allowed):**
```bash
git checkout main
git merge --no-ff feat/new-feature
# ✅ Allowed (MERGE_HEAD bypass)
# ✅ Security checks still run
```



### pre-commit

Runs before each commit to validate (ordered by fail-fast principle):

1. **Session/Branch Identity** (all commits) ⚡ **CRITICAL - FAIL FAST**
   - Validates session matches current branch
   - Prevents cross-session branch contamination
   - Blocks commits to wrong branch immediately
   - Runs `tools/validators/session-branch-validator.sh`
   - See: `.claude/rules/branch-context.md` for enforcement system

2. **Secrets Detection** (code files only) 🔒 **CRITICAL**
   - Detects: `password`, `secret`, `token`, `api_key`, `private_key`, `aws_secret` in assignment patterns
   - Excludes documentation files (`.md`, `.txt`, `.rst`) to prevent false positives
   - Looks for actual assignments like `API_KEY = "value"`, not just keyword mentions
   - Prevents accidental credential commits

3. **Large File Detection** (all commits) 🔒 **CRITICAL**
   - Blocks files larger than 5MB
   - Suggests using Git LFS for large files
   - Prevents repository bloat

4. **Root Directory Validation** (all commits)
   - Enforces clean root directory (max 13 allowed files)
   - Blocks new files not in allowlist
   - See AGENTS.md Section 9 for file placement rules

5. **Fidelity Validation** (feature branches only - Tier 2)
   - Validates naming conventions (camelCase, PascalCase, UPPER_SNAKE_CASE)
   - Checks code follows documented patterns
   - Blocks CRITICAL violations, reports warnings
   - Runs `tools/validators/fidelity_validators.py`

6. **Code of Conduct Changes** (conditional - only if CoC files modified)
   - Validates structure against schema
   - Ensures all rules and prohibitions are documented
   - Runs `tools/validators/conduct-validator.py`

**Example output:**
```
🔍 Validating session/branch identity...
✅ Session/Branch Match Validated

🔍 Checking for secrets...
✅ No secrets detected

🔍 Checking file sizes...
✅ All files are within size limits

🔍 Checking root directory organization...
✅ Root directory organization is clean

🔍 Running fidelity checks...
✅ Fidelity checks passed
```

**Validation Order Rationale:**
The checks are ordered by the **fail-fast principle** - critical, fast checks run first:
- **Session/Branch Identity first** - If wrong branch, fail immediately (foundation of parallel workflow safety)
- **Security checks next** - Never commit secrets
- **Fast checks before slow** - File size before AST parsing
- **Conditional checks last** - Code of Conduct only when relevant files change

### commit-msg

Validates commit message format before allowing commits.

**Required Format:**
```
type(scope): description
```

**Valid Types:**
- `feat` - A new feature
- `fix` - A bug fix
- `docs` - Documentation only changes
- `style` - Code style changes (formatting, etc)
- `refactor` - Code refactoring
- `perf` - Performance improvements
- `test` - Adding or updating tests
- `chore` - Maintenance tasks (dependencies, tooling)
- `ci` - CI/CD configuration changes

**Scope:** Optional (e.g., `auth`, `api`, `ui`)

**Examples of valid messages:**
```bash
feat(auth): add JWT token validation
fix(api): handle null response in user endpoint
docs: update README with installation steps
chore: update dependencies
test(utils): add validation tests
```

**Examples of invalid messages:**
```bash
invalid message                    # Missing type
added new feature                  # Not conventional format
feat add feature                   # Missing colon
feat: ab                          # Description too short (<3 chars)
```

**Example output:**
```
❌ INVALID COMMIT MESSAGE FORMAT

Expected format:
  type(scope): description
  type: description

Valid types:
  feat, fix, docs, style, refactor, perf, test, chore, ci

Examples:
  feat(auth): add JWT token validation
  fix(api): handle null response in user endpoint
  docs: update README with installation steps
```

### pre-commit-config

Validates configuration file changes before allowing commits.

**Validates:**
- `.opencode/profiles/*.json` - Profile configurations
- `.opencode/oh-my-opencode.json` - Active profile symlink
- `AGENTS.md` - Agent roster and routing
- `.opencode/skills/*.md` - Skill definitions
- `.claude/commands/*.md` - Command definitions

**Runs 3 validators:**
1. `profile-comparator.py` - Checks profile consistency
2. `routing-verifier.py` - Verifies routing configuration
3. `doc-sync-checker.py` - Checks documentation sync

**Example output:**
```
🔍 Validating configuration changes...
  → Checking profile consistency...
    ✅ Profile consistency check passed
  → Verifying routing configuration...
    ✅ Routing verification passed
  → Checking documentation sync...
    ✅ Documentation sync check passed
✅ Configuration validation passed
```

## Bypassing Hooks

**⚠️ Not Recommended** - Hooks exist to prevent issues.

If you absolutely need to bypass hooks (e.g., emergency hotfix):

```bash
git commit --no-verify -m "emergency: fix critical bug"
```

**When bypassing is acceptable:**
- Emergency hotfixes (fix first, clean up later)
- Reverting a broken commit
- Working on a WIP branch that will be squashed

**When bypassing is NOT acceptable:**
- Committing secrets or credentials
- Committing large files without Git LFS
- Avoiding proper commit message format
- Skipping configuration validation

## Testing Hooks

### Test commit-msg hook

```bash
# Test invalid message (should FAIL)
git commit --allow-empty -m "invalid message"

# Test valid message with scope (should SUCCEED)
git commit --allow-empty -m "feat(test): add validation"

# Test valid message without scope (should SUCCEED)
git commit --allow-empty -m "docs: update readme"

# Test all valid types
for type in feat fix docs style refactor perf test chore ci; do
    git commit --allow-empty -m "$type: test message"
done
```

### Test secrets detection

```bash
# Test with API key (should FAIL)
echo "API_KEY=sk_live_123456" > test.env
git add test.env
git commit -m "test: add env file"
# Expected: ❌ Potential secrets detected

# Cleanup
git reset HEAD test.env
rm test.env

# Test with password (should FAIL)
echo "password=secret123" > test.env
git add test.env
git commit -m "test: add env file"
# Expected: ❌ Potential secrets detected

# Cleanup
git reset HEAD test.env
rm test.env

# Test with clean file (should SUCCEED)
echo "# clean config" > test.txt
git add test.txt
git commit -m "test: add config"
# Expected: ✅ All checks passed

# Cleanup
git reset HEAD test.txt
rm test.txt
```

### Test large file detection

```bash
# Test with large file (should FAIL)
dd if=/dev/zero of=large.bin bs=1M count=6
git add large.bin
git commit -m "test: add large file"
# Expected: ❌ Large file detected

# Cleanup
git reset HEAD large.bin
rm large.bin

# Test with small file (should SUCCEED)
dd if=/dev/zero of=small.bin bs=1M count=1
git add small.bin
git commit -m "test: add small file"
# Expected: ✅ All checks passed

# Cleanup
git reset HEAD small.bin
rm small.bin
```

### Test Code of Conduct validation

```bash
# Modify CODE_OF_CONDUCT.md
echo "# Test" >> CODE_OF_CONDUCT.md
git add CODE_OF_CONDUCT.md
git commit -m "test: modify CoC"
# Expected: Validation runs (may pass or fail depending on changes)

# Cleanup
git reset HEAD CODE_OF_CONDUCT.md
git checkout CODE_OF_CONDUCT.md
```

## Troubleshooting

### Hooks not running

**Symptom:** Commits succeed without any hook output

**Check:**
```bash
git config core.hooksPath
```

**Expected:** `.githooks`

**Solution:**
```bash
git config core.hooksPath .githooks
```

### Permission denied

**Symptom:** `bash: .githooks/pre-commit: Permission denied`

**Solution:**
```bash
chmod +x .githooks/*
```

### Hooks not installed after clone

**Symptom:** Fresh clone doesn't have hooks configured

**Solution:**
```bash
git config core.hooksPath .githooks
```

**Prevention:** Add to onboarding documentation or use `git config --global core.hooksPath .githooks` (applies to all repos).

### Python validator errors

**Symptom:** `python3: command not found` or `validator.py not found`

**Check:**
```bash
# Check Python 3 is installed
python3 --version

# Check validators exist
ls tools/validators/*.py
```

**Solution:**
- Install Python 3: `sudo apt install python3` (Ubuntu) or `brew install python3` (macOS)
- Ensure validators exist in `tools/validators/`

**Note:** Hooks gracefully degrade if validators are missing (warnings only, commits not blocked).

### Hook exits with error

**Symptom:** Hook fails with unexpected error

**Debug:**
```bash
# Run hook manually to see full output
bash .githooks/pre-commit

# Or for commit-msg
echo "test: message" | bash .githooks/commit-msg /dev/stdin
```

### Secrets detected in legitimate code

**Symptom:** Hook blocks commit with false positive (e.g., variable named `password` in code)

**Note:** Documentation files (`.md`, `.txt`, `.rst`) are automatically excluded from secrets detection.

**Options:**
1. **Check if it's a real secret** - The hook only flags assignment patterns like `API_KEY = "value"`
2. **Rename variable** (if appropriate): Use `pwd`, `pass`, `cred` instead
3. **Bypass this commit** (use sparingly): `git commit --no-verify`
4. **Update hook pattern** (advanced): Edit `.githooks/pre-commit` to refine regex

## Adding New Hooks

To add a new hook to the system:

### 1. Create hook file

```bash
# Create new hook
touch .githooks/pre-push
chmod +x .githooks/pre-push
```

### 2. Add hook logic

```bash
#!/bin/bash
#
# Pre-Push Hook
# Description of what this hook does
#

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Redirect output to stderr
exec 1>&2

# Find repository root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
    echo -e "${RED}❌ ERROR: Not in a git repository${NC}"
    exit 1
fi

# Your validation logic here
echo -e "${BLUE}🔍 Running pre-push checks...${NC}"

# Exit 0 for success, non-zero for failure
exit 0
```

### 3. Test hook

```bash
# Test manually
bash .githooks/pre-push

# Test with git
git push origin feature-branch
```

### 4. Update this README

Add documentation for the new hook in the "Available Hooks" section.

### 5. Commit changes

```bash
git add .githooks/pre-push .githooks/README.md
git commit -m "feat(hooks): add pre-push validation"
```

## Hook Execution Order

Hooks run in this order during a commit:

1. **pre-commit** - Validates Code of Conduct, secrets, file sizes
2. **commit-msg** - Validates commit message format
3. **pre-commit-config** - Validates configuration files (if modified)

If any hook fails (exits non-zero), the commit is aborted.

## Best Practices

### For Developers

- ✅ **Read error messages carefully** - They include examples and solutions
- ✅ **Test hooks locally** before pushing
- ✅ **Use conventional commit format** - It enables automated changelogs
- ✅ **Keep commits small** - Easier to validate and review
- ✅ **Never commit secrets** - Use environment variables or secret managers

### For Maintainers

- ✅ **Keep hooks fast** - Slow hooks frustrate developers
- ✅ **Provide clear error messages** - Include examples and solutions
- ✅ **Graceful degradation** - Don't block if tools are missing
- ✅ **Document all hooks** - Keep this README up to date
- ✅ **Test hooks thoroughly** - Use the testing procedures above

## Resources

- **Git Hooks Documentation:** https://git-scm.com/docs/githooks
- **Conventional Commits:** https://www.conventionalcommits.org/
- **Git LFS:** https://git-lfs.github.com/
- **Code of Conduct:** `CODE_OF_CONDUCT.md`
- **Validators:** `tools/validators/`

## Support

If you encounter issues with hooks:

1. Check this troubleshooting guide
2. Run hooks manually to see full error output
3. Check `tools/validators/` for validator documentation
4. Ask in team chat or create an issue

---

**Last Updated:** January 26, 2026  
**Maintained by:** astraeus team

### 1. Session/Branch Identity Validation (NEW - v0.3.0, moved to position #1 in v0.3.1)

**⚡ CRITICAL - FAIL FAST** - Prevents cross-session branch contamination in parallel workflows.

**Why this is first:** If you're committing to the wrong branch, all other validations are pointless. This check is fast (file read + git command) and critical, so it runs before everything else to provide immediate feedback.

**Validates:**
- Session identity matches current branch
- Not committing directly to main/master
- Session was initialized via `/init`

**Example output:**
```
🔍 Validating session/branch identity...
✅ Session/Branch Match Validated
  Session: opencode-abc123
  Branch:  fix/deployment-gaps-issue-59 (LOCKED)
```

**If session/branch mismatch:**
```
❌ SESSION/BRANCH MISMATCH - COMMIT BLOCKED

Session Identity:
  Session ID:    opencode-abc123
  Locked Branch: feat/authentication

Current State:
  Current Branch: feat/api-changes

Problem:
  Your session is locked to 'feat/authentication' but you're trying to
  commit to 'feat/api-changes'. This indicates cross-session contamination.

Solution:
  1. Restore your branch: git checkout feat/authentication
  2. Or use: ./tools/session-identity.sh restore
  3. Then retry your commit
```

**CRITICAL for parallel sessions:**
When running multiple agent sessions in the same repository:
- Session A locks to branch-a
- Session B locks to branch-b
- If Session A runs `git fetch`, HEAD may change
- Session B MUST restore: `./tools/session-identity.sh restore` before next operation

**After any `git fetch` or `git pull`:**
```bash
git fetch upstream
./tools/session-identity.sh restore  # ← MANDATORY
```

This prevents agents from "falling into" each other's branches after upstream sync operations.

**Merge and Cherry-pick Commits:**

Merge commits and cherry-picks are allowed on main/master:
- `.git/MERGE_HEAD` exists → Merge commit allowed, all validation skipped
- `.git/CHERRY_PICK_HEAD` exists → Cherry-pick allowed, all validation skipped
- All security checks still run (secrets, file size, etc.)
- Changelog fragment check skipped (already validated on source branch)

Example: Merging a PR branch to main:
```bash
git checkout main
git merge --no-ff feat/new-feature -m "Merge PR #123"
# ✅ Merge commit to main — allowed
# ⚠️  Merge commit — fragment check skipped
```

Direct commits to main still blocked:
```bash
git checkout main
echo "change" >> file.txt
git commit -m "direct change"
# ❌ COMMIT TO DEFAULT BRANCH BLOCKED
```

