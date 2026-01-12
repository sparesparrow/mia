#!/bin/bash
# Restore CPY Symlinks for MIA Project
# Creates symlinks from _Build directory to central ~/CPY/packages

set -e

echo "🔗 Restoring CPY symlinks for MIA project..."

# Create _Build directory structure
mkdir -p _Build/SOURCE/EXTERNAL_DEPENDENCIES/{foundation,embedded,mcp,consumers}

# Create symlinks to central CPY packages
cd _Build/SOURCE/EXTERNAL_DEPENDENCIES

# Foundation packages
ln -sf ~/CPY/packages/foundation/sparetools-base foundation/
ln -sf ~/CPY/packages/foundation/sparetools-cpython foundation/
ln -sf ~/CPY/packages/foundation/sparetools-bootstrap foundation/

# Embedded packages
ln -sf ~/CPY/packages/embedded/sparetools-embedded embedded/
ln -sf ~/CPY/packages/embedded/sparetools-hal-sunton embedded/
ln -sf ~/CPY/packages/embedded/sparetools-flatbuffers embedded/

# MCP packages
ln -sf ~/CPY/packages/mcp/sparetools-mcp-core mcp/
ln -sf ~/CPY/packages/mcp/sparetools-mcp-orchestrator mcp/

# Consumer packages
ln -sf ~/CPY/packages/consumers/sparetools-mia consumers/

echo "✅ CPY symlinks restored successfully"
echo "📁 Build artifacts will appear in _Build/SOURCE/EXTERNAL_DEPENDENCIES/"