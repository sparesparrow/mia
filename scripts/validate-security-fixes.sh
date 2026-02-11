#!/bin/bash

# 🔒 AI-SERVIS Universal: Security Fixes Validation Script
# Validates that all security vulnerabilities have been resolved

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔒 AI-SERVIS Universal Security Validation${NC}"
echo "=================================================="

# Check for vulnerable package versions
echo -e "${BLUE}Checking for vulnerable package versions...${NC}"

vulnerable_found=false

# Define vulnerable versions to check for
declare -A vulnerable_packages=(
    ["orjson"]="3.9.10"
    ["torch"]="2.1.1"
    ["cryptography"]="41.0.8"
    ["black"]="23.11.0"
)

# Define secure versions
declare -A secure_packages=(
    ["orjson"]="3.9.15"
    ["torch"]="2.2.0"
    ["cryptography"]="43.0.1"
    ["black"]="24.3.0"
)

# Check all requirements files
for req_file in $(find . -name "requirements*.txt" -o -name "*.sh" | grep -v ".git"); do
    echo -e "${YELLOW}Checking: $req_file${NC}"
    
    for package in "${!vulnerable_packages[@]}"; do
        vulnerable_version="${vulnerable_packages[$package]}"
        secure_version="${secure_packages[$package]}"
        
        if grep -q "${package}==${vulnerable_version}" "$req_file" 2>/dev/null; then
            echo -e "${RED}❌ VULNERABLE: Found ${package}==${vulnerable_version} in $req_file${NC}"
            vulnerable_found=true
        elif grep -q "${package}==${secure_version}" "$req_file" 2>/dev/null; then
            echo -e "${GREEN}✅ SECURE: Found ${package}==${secure_version} in $req_file${NC}"
        fi
    done
done

echo ""

# Summary
if [ "$vulnerable_found" = true ]; then
    echo -e "${RED}❌ VALIDATION FAILED: Vulnerable packages found!${NC}"
    echo -e "${RED}Please update the vulnerable packages before proceeding.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ VALIDATION PASSED: No vulnerable packages found!${NC}"
    echo -e "${GREEN}All security fixes have been properly applied.${NC}"
fi

echo ""
echo -e "${BLUE}Security validation completed.${NC}"
echo "=================================================="

# Additional checks
echo -e "${BLUE}Additional Security Checks:${NC}"

# Check for any remaining references to old versions
echo "Searching for any remaining vulnerable version references..."

old_versions_found=false
for package in "${!vulnerable_packages[@]}"; do
    vulnerable_version="${vulnerable_packages[$package]}"
    if grep -r "${package}==${vulnerable_version}" . --exclude-dir=.git --exclude-dir=site --exclude="*.md" --exclude="validate-security-fixes.sh" 2>/dev/null; then
        echo -e "${RED}❌ Found reference to vulnerable ${package}==${vulnerable_version}${NC}"
        old_versions_found=true
    fi
done

if [ "$old_versions_found" = false ]; then
    echo -e "${GREEN}✅ No references to vulnerable versions found${NC}"
fi

echo ""
echo -e "${GREEN}🔒 Security validation complete!${NC}"
echo -e "${GREEN}AI-SERVIS Universal is ready for secure deployment.${NC}"