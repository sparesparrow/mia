#!/bin/bash
# Script to analyze kernun web interface implementation
# Usage: ./analyze-kernun-interface.sh [IP_ADDRESS]

set -e

KERNUN_HOST="${1:-192.168.200.23}"
KERNUN_USER="${KERNUN_USER:-sparrow}"
KERNUN_PATH="/home/sparrow/Desktop/kernun"
OUTPUT_DIR="$(pwd)/kernun-analysis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Kernun Web Interface Analysis ==="
echo "Host: ${KERNUN_USER}@${KERNUN_HOST}"
echo "Path: ${KERNUN_PATH}"
echo "Output: ${OUTPUT_DIR}"
echo ""

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Function to execute remote command
remote_cmd() {
    ssh "${KERNUN_USER}@${KERNUN_HOST}" "$@"
}

# Function to copy remote file/directory
remote_copy() {
    scp -r "${KERNUN_USER}@${KERNUN_HOST}:${1}" "${2}"
}

echo "1. Listing directory structure..."
remote_cmd "find ${KERNUN_PATH} -type f -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.json' -o -name '*.py' -o -name '*.cpp' -o -name '*.h' | head -100" > "${OUTPUT_DIR}/file_list.txt"

echo "2. Analyzing frontend structure..."
remote_cmd "ls -la ${KERNUN_PATH}" > "${OUTPUT_DIR}/directory_structure.txt"

# Look for common web interface directories
for dir in web www frontend ui interface public src static assets; do
    if remote_cmd "test -d ${KERNUN_PATH}/${dir}" 2>/dev/null; then
        echo "   Found ${dir}/ directory"
        remote_cmd "find ${KERNUN_PATH}/${dir} -type f | head -50" >> "${OUTPUT_DIR}/frontend_files.txt"
    fi
done

echo "3. Analyzing backend integration..."
# Look for backend/server files
remote_cmd "find ${KERNUN_PATH} -type f \( -name '*server*' -o -name '*api*' -o -name '*backend*' \) | head -20" > "${OUTPUT_DIR}/backend_files.txt"

echo "4. Analyzing C++ integration..."
# Look for C++ files that might interface with web
remote_cmd "find ${KERNUN_PATH} -type f \( -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) | grep -E '(web|http|api|server|ui)' | head -20" > "${OUTPUT_DIR}/cpp_integration_files.txt"

echo "5. Analyzing configuration files..."
remote_cmd "find ${KERNUN_PATH} -type f \( -name '*.json' -o -name '*.yaml' -o -name '*.yml' -o -name '*.conf' -o -name '*.config' -o -name 'package.json' -o -name 'CMakeLists.txt' \) | head -30" > "${OUTPUT_DIR}/config_files.txt"

echo "6. Checking for WebSocket/real-time features..."
remote_cmd "grep -r 'websocket\|WebSocket\|ws://\|wss://' ${KERNUN_PATH} --include='*.js' --include='*.py' --include='*.cpp' --include='*.h' 2>/dev/null | head -20" > "${OUTPUT_DIR}/websocket_usage.txt" || echo "No WebSocket usage found"

echo "7. Checking for systemd integration..."
remote_cmd "grep -r 'systemd\|systemctl' ${KERNUN_PATH} --include='*.py' --include='*.sh' --include='*.cpp' 2>/dev/null | head -20" > "${OUTPUT_DIR}/systemd_integration.txt" || echo "No systemd integration found"

echo "8. Checking for D-Bus or IPC mechanisms..."
remote_cmd "grep -r 'dbus\|D-Bus\|zmq\|ZeroMQ\|unix.*socket' ${KERNUN_PATH} --include='*.py' --include='*.cpp' --include='*.h' 2>/dev/null | head -20" > "${OUTPUT_DIR}/ipc_mechanisms.txt" || echo "No IPC mechanisms found"

echo "9. Analyzing package.json (if exists)..."
if remote_cmd "test -f ${KERNUN_PATH}/package.json" 2>/dev/null; then
    remote_cmd "cat ${KERNUN_PATH}/package.json" > "${OUTPUT_DIR}/package.json"
    echo "   Extracted package.json"
fi

echo "10. Analyzing main HTML entry point..."
for html_file in index.html main.html app.html; do
    if remote_cmd "test -f ${KERNUN_PATH}/${html_file}" 2>/dev/null; then
        remote_cmd "head -100 ${KERNUN_PATH}/${html_file}" > "${OUTPUT_DIR}/${html_file}.sample"
        echo "   Found ${html_file}"
    fi
done

echo "11. Creating summary report..."
cat > "${OUTPUT_DIR}/ANALYSIS_SUMMARY.md" <<EOF
# Kernun Web Interface Analysis Summary

**Analysis Date**: $(date)
**Source**: ${KERNUN_USER}@${KERNUN_HOST}:${KERNUN_PATH}

## Directory Structure
\`\`\`
$(cat "${OUTPUT_DIR}/directory_structure.txt")
\`\`\`

## Key Findings

### Frontend Technology
- Check \`package.json\` for framework and dependencies
- Review \`frontend_files.txt\` for component structure

### Backend Integration
- Review \`backend_files.txt\` for API structure
- Check for REST endpoints and WebSocket usage

### C++ Integration
- Review \`cpp_integration_files.txt\` for IPC mechanisms
- Check \`ipc_mechanisms.txt\` for communication patterns

### System Integration
- Review \`systemd_integration.txt\` for service management
- Check configuration files for system settings

## Next Steps

1. Review extracted files in this directory
2. Identify key patterns and architectures
3. Document findings in MIA web interface plan
4. Adapt successful patterns to MIA implementation

## Files Generated

- \`file_list.txt\`: Complete list of relevant files
- \`directory_structure.txt\`: Top-level directory structure
- \`frontend_files.txt\`: Frontend source files
- \`backend_files.txt\`: Backend/server files
- \`cpp_integration_files.txt\`: C++ integration files
- \`config_files.txt\`: Configuration files
- \`websocket_usage.txt\`: WebSocket implementation
- \`systemd_integration.txt\`: Systemd service management
- \`ipc_mechanisms.txt\`: IPC communication patterns
EOF

echo ""
echo "=== Analysis Complete ==="
echo "Results saved to: ${OUTPUT_DIR}"
echo ""
echo "To review the analysis:"
echo "  cat ${OUTPUT_DIR}/ANALYSIS_SUMMARY.md"
echo "  ls -la ${OUTPUT_DIR}"
