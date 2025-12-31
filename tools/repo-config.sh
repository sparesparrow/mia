#!/bin/bash
# MIA Universal Repository Configuration Helper
# Switch between different package repositories and manage authentication

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Repository configurations
declare -A REPOSITORIES=(
    ["cloudsmith"]="https://cloudsmith.io/~sparetools/repos/sparetools/packages/"
    ["github-packages"]="https://maven.pkg.github.com/sparetools"
    ["conancenter"]="https://center.conan.io"
    ["artifactory-local"]="http://localhost:8081/artifactory/api/conan/conan-local"
)

# Check if Conan is available
check_conan() {
    if ! command -v conan &> /dev/null; then
        log_error "Conan not found in PATH. Run ./tools/bootstrap.sh first"
        exit 1
    fi
}

# List configured remotes
list_remotes() {
    log_info "Currently configured Conan remotes:"
    echo

    if ! conan remote list; then
        log_error "Failed to list Conan remotes"
        return 1
    fi

    echo
    log_info "Available repository options:"
    echo "  cloudsmith       - Cloudsmith (recommended for MIA)"
    echo "  github-packages  - GitHub Packages (fallback)"
    echo "  conancenter      - Conan Center (public packages)"
    echo "  artifactory-local- Local Artifactory (development)"
}

# Add a repository remote
add_remote() {
    local name="$1"
    local url="$2"

    log_info "Adding Conan remote: $name"

    if conan remote add "$name" "$url" --force; then
        log_success "Remote '$name' added successfully"
        return 0
    else
        log_error "Failed to add remote '$name'"
        return 1
    fi
}

# Remove a repository remote
remove_remote() {
    local name="$1"

    log_info "Removing Conan remote: $name"

    if conan remote remove "$name"; then
        log_success "Remote '$name' removed successfully"
        return 0
    else
        log_error "Failed to remove remote '$name'"
        return 1
    fi
}

# Login to a repository
login_remote() {
    local name="$1"
    local username="$2"
    local password="$3"

    log_info "Logging in to remote: $name"

    # Try to login
    if echo "$password" | conan remote login "$name" "$username"; then
        log_success "Successfully logged in to '$name'"
        return 0
    else
        log_error "Failed to login to '$name'"
        return 1
    fi
}

# Setup Cloudsmith repository
setup_cloudsmith() {
    local username="$1"
    local api_key="$2"

    if [ -z "$username" ]; then
        read -p "Enter Cloudsmith username: " username
    fi

    if [ -z "$api_key" ]; then
        read -s -p "Enter Cloudsmith API key: " api_key
        echo
    fi

    if [ -z "$username" ] || [ -z "$api_key" ]; then
        log_error "Username and API key are required for Cloudsmith"
        return 1
    fi

    # Add remote
    if ! add_remote "sparetools" "${REPOSITORIES[cloudsmith]}"; then
        return 1
    fi

    # Login
    if ! login_remote "sparetools" "$username" "$api_key"; then
        return 1
    fi

    log_success "Cloudsmith repository configured successfully"
}

# Setup GitHub Packages repository
setup_github_packages() {
    local username="$1"
    local token="$2"

    if [ -z "$username" ]; then
        read -p "Enter GitHub username: " username
    fi

    if [ -z "$token" ]; then
        read -s -p "Enter GitHub personal access token: " token
        echo
    fi

    if [ -z "$username" ] || [ -z "$token" ]; then
        log_error "Username and token are required for GitHub Packages"
        return 1
    fi

    # Add remote
    if ! add_remote "github-sparetools" "${REPOSITORIES[github-packages]}"; then
        return 1
    fi

    # Login (GitHub Packages uses token as password)
    if ! login_remote "github-sparetools" "$username" "$token"; then
        return 1
    fi

    log_success "GitHub Packages repository configured successfully"
}

# Setup Conan Center (public)
setup_conancenter() {
    if ! add_remote "conancenter" "${REPOSITORIES[conancenter]}"; then
        return 1
    fi

    log_success "Conan Center configured (no authentication required)"
}

# Setup local Artifactory (development)
setup_artifactory_local() {
    if ! add_remote "artifactory-local" "${REPOSITORIES[artifactory-local]}"; then
        return 1
    fi

    log_success "Local Artifactory configured"
}

# Test repository connectivity
test_repository() {
    local name="$1"

    log_info "Testing connectivity to '$name'..."

    # Try to list packages (this tests connectivity and authentication)
    if conan search "*" -r "$name" --raw > /dev/null 2>&1; then
        log_success "Repository '$name' is accessible"
        return 0
    else
        log_error "Repository '$name' is not accessible"
        return 1
    fi
}

# Get repository priority
get_priority() {
    local name="$1"

    case "$name" in
        "sparetools")
            echo 100
            ;;
        "github-sparetools")
            echo 90
            ;;
        "conancenter")
            echo 50
            ;;
        "artifactory-local")
            echo 10
            ;;
        *)
            echo 0
            ;;
    esac
}

# Setup repository with priority
setup_repository_priority() {
    log_info "Setting up repository priorities..."

    # Get list of remotes
    local remotes=($(conan remote list | awk '{print $1}' | grep -v "^Remote" | grep -v "^$" || true))

    # Sort remotes by priority (highest first)
    local sorted_remotes=()
    for remote in "${remotes[@]}"; do
        sorted_remotes+=("$remote:$(get_priority "$remote")")
    done

    # Sort by priority (descending)
    IFS=$'\n' sorted_remotes=($(sort -t: -k2 -nr <<<"${sorted_remotes[*]}"))
    unset IFS

    # Set priorities (0 = highest priority)
    local priority=0
    for item in "${sorted_remotes[@]}"; do
        local remote="${item%%:*}"
        conan remote set-update-index "$remote" $priority > /dev/null 2>&1 || true
        ((priority++))
    done

    log_info "Repository priorities updated"
}

# Interactive repository setup
interactive_setup() {
    echo
    log_info "Interactive Repository Setup"
    echo "Choose repositories to configure:"
    echo "1) Cloudsmith (recommended for MIA packages)"
    echo "2) GitHub Packages (fallback)"
    echo "3) Conan Center (public packages)"
    echo "4) Local Artifactory (development)"
    echo "5) Skip setup"
    echo

    local choice
    read -p "Enter your choice (1-5): " choice

    case $choice in
        1)
            setup_cloudsmith
            ;;
        2)
            setup_github_packages
            ;;
        3)
            setup_conancenter
            ;;
        4)
            setup_artifactory_local
            ;;
        5)
            log_info "Skipping repository setup"
            return 0
            ;;
        *)
            log_error "Invalid choice"
            return 1
            ;;
    esac

    # Setup priorities after adding repositories
    setup_repository_priority
}

# Print usage information
print_usage() {
    cat << 'EOF'
MIA Universal Repository Configuration Helper

Usage: repo-config.sh [COMMAND] [OPTIONS]

Commands:
    list                List configured remotes
    add <name> <url>    Add a new remote
    remove <name>      Remove a remote
    login <name>       Login to a remote (interactive)
    setup              Interactive repository setup
    test <name>        Test connectivity to a remote
    priority           Setup repository priorities

Repository Shortcuts:
    cloudsmith          Setup Cloudsmith repository
    github              Setup GitHub Packages repository
    conancenter         Setup Conan Center
    artifactory         Setup local Artifactory

Options:
    --username USER     Repository username
    --password PASS     Repository password/token
    --help             Show this help message

Examples:
    ./tools/repo-config.sh list
    ./tools/repo-config.sh setup
    ./tools/repo-config.sh cloudsmith --username myuser --password mykey
    ./tools/repo-config.sh test sparetools

Environment Variables:
    CLOUDSMITH_USERNAME    Cloudsmith username
    CLOUDSMITH_API_KEY     Cloudsmith API key
    GITHUB_USERNAME        GitHub username
    GITHUB_TOKEN           GitHub personal access token
EOF
}

# Main function
main() {
    check_conan

    if [ $# -eq 0 ]; then
        interactive_setup
        exit $?
    fi

    local command="$1"
    shift

    case "$command" in
        list)
            list_remotes
            ;;
        add)
            if [ $# -lt 2 ]; then
                log_error "Usage: $0 add <name> <url>"
                exit 1
            fi
            add_remote "$1" "$2"
            setup_repository_priority
            ;;
        remove)
            if [ $# -lt 1 ]; then
                log_error "Usage: $0 remove <name>"
                exit 1
            fi
            remove_remote "$1"
            setup_repository_priority
            ;;
        login)
            if [ $# -lt 1 ]; then
                log_error "Usage: $0 login <name>"
                exit 1
            fi
            # Interactive login
            local username password
            read -p "Username: " username
            read -s -p "Password/Token: " password
            echo
            login_remote "$1" "$username" "$password"
            ;;
        setup)
            interactive_setup
            ;;
        test)
            if [ $# -lt 1 ]; then
                log_error "Usage: $0 test <name>"
                exit 1
            fi
            test_repository "$1"
            ;;
        priority)
            setup_repository_priority
            ;;
        cloudsmith)
            local username="" password=""
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --username)
                        username="$2"
                        shift 2
                        ;;
                    --password)
                        password="$2"
                        shift 2
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            setup_cloudsmith "$username" "$password"
            setup_repository_priority
            ;;
        github)
            local username="" password=""
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --username)
                        username="$2"
                        shift 2
                        ;;
                    --password)
                        password="$2"
                        shift 2
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            setup_github_packages "$username" "$password"
            setup_repository_priority
            ;;
        conancenter)
            setup_conancenter
            setup_repository_priority
            ;;
        artifactory)
            setup_artifactory_local
            setup_repository_priority
            ;;
        --help|-h)
            print_usage
            ;;
        *)
            log_error "Unknown command: $command"
            echo
            print_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"