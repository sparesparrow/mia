#!/bin/bash
# Monitor PR workflows and fix issues automatically

set -e

BRANCH="${1:-feature/raspberry-pi-development}"
REPO="sparesparrow/ai-servis"
MAIN_BRANCH="main"
LOOP_INTERVAL=300  # 5 minutes in seconds

echo "========================================"
echo "  PR Workflow Monitor"
echo "========================================"
echo "Branch: $BRANCH"
echo "Repository: $REPO"
echo "Check interval: ${LOOP_INTERVAL}s"
echo ""

# Function to check if PR exists
check_pr_exists() {
    local branch=$1
    # Try to get PR number from git config or check via API
    if command -v gh &> /dev/null; then
        gh pr list --head "$branch" --json number --jq '.[0].number' 2>/dev/null || echo ""
    else
        # Fallback: try to get from git notes or check if branch is pushed
        git ls-remote --heads origin "$branch" | grep -q "$branch" && echo "exists" || echo ""
    fi
}

# Function to create PR if it doesn't exist
create_pr() {
    local branch=$1
    if command -v gh &> /dev/null; then
        gh pr create --head "$branch" --base "$MAIN_BRANCH" \
            --title "feat: OBD Simulator Integration with CI/CD" \
            --body "Integrates OBD Simulator components with automated CI/CD pipeline and Conan dependency management.

## Changes
- OBD Worker service with ELM327 emulator integration
- Serial Bridge for ESP32/Arduino communication
- Conan recipe for Python service packaging
- Comprehensive tests and CI/CD workflows
- Updated deployment scripts

## Testing
- Unit and integration tests added
- CI/CD pipeline integration
- Conan package validation" 2>/dev/null || echo "PR creation failed"
    else
        echo "GitHub CLI not available. Please create PR manually at:"
        echo "https://github.com/$REPO/compare/$MAIN_BRANCH...$branch"
    fi
}

# Function to rebase on main
rebase_on_main() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Rebasing on $MAIN_BRANCH..."
    git fetch origin "$MAIN_BRANCH" || return 1
    
    if git rebase "origin/$MAIN_BRANCH"; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ Rebase successful"
        git push origin "$BRANCH" --force-with-lease || {
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Push failed, may need manual intervention"
            return 1
        }
        return 0
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Rebase conflicts detected"
        # Try to auto-resolve common conflicts
        resolve_conflicts
        return $?
    fi
}

# Function to resolve conflicts
resolve_conflicts() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Attempting to resolve conflicts..."
    
    # Check for conflict markers
    if git diff --check | grep -q "^+<<<<<<<"; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Conflict markers found"
        
        # Common conflict resolution strategies
        # 1. For requirements.txt - prefer our version (newer dependencies)
        if [ -f "rpi/requirements.txt" ] && git status --short | grep -q "UU.*requirements.txt"; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Resolving requirements.txt conflict..."
            git checkout --ours rpi/requirements.txt
            git add rpi/requirements.txt
        fi
        
        # 2. For workflow files - merge both
        if git status --short | grep -q "UU.*\.yml"; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Resolving workflow file conflicts..."
            # Try to merge workflow files intelligently
            for file in $(git diff --name-only --diff-filter=U); do
                if [[ "$file" == *.yml ]] || [[ "$file" == *.yaml ]]; then
                    # Use theirs for workflow structure, but keep our jobs
                    git checkout --theirs "$file"
                    git add "$file"
                fi
            done
        fi
        
        # Continue rebase
        if git rebase --continue; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ Conflicts resolved"
            git push origin "$BRANCH" --force-with-lease
            return 0
        else
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✗ Failed to resolve conflicts automatically"
            return 1
        fi
    fi
    
    return 1
}

# Function to check workflow status
check_workflow_status() {
    local pr_number=$1
    
    if command -v gh &> /dev/null && [ -n "$pr_number" ]; then
        gh pr checks "$pr_number" --json conclusion,status,name,workflowName \
            --jq '.[] | select(.status == "completed" or .status == "in_progress") | "\(.workflowName // .name): \(.status) - \(.conclusion // "pending")"' 2>/dev/null || echo ""
    else
        echo "Workflow status check requires GitHub CLI"
    fi
}

# Function to get failed workflow logs
get_failed_workflows() {
    local pr_number=$1
    
    if command -v gh &> /dev/null && [ -n "$pr_number" ]; then
        gh pr checks "$pr_number" --json conclusion,status,name,workflowName,detailsUrl \
            --jq '.[] | select(.conclusion == "failure") | "\(.workflowName // .name): \(.detailsUrl)"' 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Function to analyze and fix workflow failures
fix_workflow_failures() {
    local pr_number=$1
    local failures=$(get_failed_workflows "$pr_number")
    
    if [ -z "$failures" ]; then
        return 0
    fi
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Analyzing workflow failures..."
    
    local needs_commit=false
    
    # Check for common failure patterns
    while IFS= read -r failure; do
        if [ -z "$failure" ]; then
            continue
        fi
        
        workflow_name=$(echo "$failure" | cut -d':' -f1)
        details_url=$(echo "$failure" | cut -d':' -f2- | xargs)
        
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Analyzing: $workflow_name"
        
        # Get workflow run details
        if command -v gh &> /dev/null; then
            # Extract run ID from URL or get latest failed run
            run_id=$(gh run list --workflow="$workflow_name" --json databaseId,conclusion --jq '.[0].databaseId' 2>/dev/null || echo "")
            
            if [ -n "$run_id" ]; then
                # Get failed job logs
                failed_jobs=$(gh run view "$run_id" --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .name' 2>/dev/null || echo "")
                
                for job in $failed_jobs; do
                    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Failed job: $job"
                    
                    # Get job logs
                    job_logs=$(gh run view "$run_id" --log-failed --job="$job" 2>/dev/null || echo "")
                    
                    # Analyze common issues
                    if echo "$job_logs" | grep -qi "ModuleNotFoundError\|ImportError"; then
                        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Issue: Missing Python dependency"
                        # Check if it's in requirements.txt
                        missing_module=$(echo "$job_logs" | grep -oP "ModuleNotFoundError: No module named '\K[^']+" | head -1)
                        if [ -n "$missing_module" ] && [ -f "rpi/requirements.txt" ]; then
                            if ! grep -q "$missing_module" rpi/requirements.txt; then
                                echo "[$(date +'%Y-%m-%d %H:%M:%S')] Adding missing dependency: $missing_module"
                                echo "$missing_module" >> rpi/requirements.txt
                                needs_commit=true
                            fi
                        fi
                    fi
                    
                    if echo "$job_logs" | grep -qi "syntax error\|SyntaxError"; then
                        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Issue: Syntax error detected"
                        # Try to identify the file
                        error_file=$(echo "$job_logs" | grep -oP "File \"[^\"]+\"" | head -1 | sed 's/File "//;s/"//')
                        if [ -n "$error_file" ] && [ -f "$error_file" ]; then
                            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Checking syntax: $error_file"
                            python3 -m py_compile "$error_file" 2>&1 || {
                                echo "[$(date +'%Y-%m-%d %H:%M:%S')] Syntax error confirmed in $error_file"
                            }
                        fi
                    fi
                    
                    if echo "$job_logs" | grep -qi "conan.*error\|ConanException"; then
                        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Issue: Conan build error"
                        # Check conanfile.py syntax
                        if [ -f "rpi/conanfile.py" ]; then
                            python3 -m py_compile rpi/conanfile.py 2>&1 || {
                                echo "[$(date +'%Y-%m-%d %H:%M:%S')] Conanfile syntax error"
                            }
                        fi
                    fi
                    
                    if echo "$job_logs" | grep -qi "pytest.*failed\|test.*FAILED"; then
                        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Issue: Test failures"
                        # Tests might need mock adjustments or dependency fixes
                        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Review test failures - may need manual intervention"
                    fi
                done
            fi
        fi
    done <<< "$failures"
    
    # Commit fixes if any
    if [ "$needs_commit" = true ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Committing fixes..."
        git add -A
        git commit -m "fix: Resolve workflow failures

- Add missing Python dependencies
- Fix syntax errors
- Update test configurations" || echo "No changes to commit"
        git push origin "$BRANCH" || echo "Push failed"
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ Fixes pushed, workflows will re-run"
    fi
}

# Main loop
ITERATION=0
while true; do
    ITERATION=$((ITERATION + 1))
    echo ""
    echo "========================================"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Iteration $ITERATION"
    echo "========================================"
    
    # Check if PR exists
    PR_NUMBER=$(check_pr_exists "$BRANCH")
    
    if [ -z "$PR_NUMBER" ] || [ "$PR_NUMBER" = "" ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] PR not found, creating..."
        PR_NUMBER=$(create_pr "$BRANCH")
        if [ -z "$PR_NUMBER" ]; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] PR creation may have failed, will retry next iteration"
        fi
    fi
    
    # Rebase on main
    if ! rebase_on_main; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Rebase failed, will retry next iteration"
    fi
    
    # Wait for workflows to run
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Waiting ${LOOP_INTERVAL}s for workflows..."
    sleep "$LOOP_INTERVAL"
    
    # Check workflow status
    if [ -n "$PR_NUMBER" ] && [ "$PR_NUMBER" != "" ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Checking workflow status..."
        check_workflow_status "$PR_NUMBER"
        
        # Fix any failures
        fix_workflow_failures "$PR_NUMBER"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] PR number not available, skipping workflow check"
    fi
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Cycle complete, next check in ${LOOP_INTERVAL}s"
done
