"""
Pytest configuration for MIA MCP modules.
Fixes import paths for test files.
"""
import sys
import os
from pathlib import Path

# Add project root to path for 'modules' imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "orchestration" / "mcp" / "modules"))

# Also add shared modules
shared_path = project_root / "orchestration" / "mcp" / "modules" / "shared"
if shared_path.exists():
    sys.path.insert(0, str(shared_path))
