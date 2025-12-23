#!/bin/bash
set -e

echo "🔧 Setting up SpareTools for MIA..."

# 1. Ensure a default Conan profile exists (required for installs on fresh runners)
echo "🧩 Ensuring Conan default profile..."
conan profile detect --force || true

# 2. Configure Conan remote
echo "📦 Configuring Conan remote..."
conan remote add sparesparrow-conan \
  https://conan.cloudsmith.io/sparesparrow-conan/sparetools/ \
  --force || true

# 3. Install SpareTools packages
echo "📥 Installing SpareTools packages..."
conan install . --build=missing -g VirtualRunEnv

# 4. Install zipapps (optional)
if [ "$1" == "--with-zipapps" ]; then
  echo "📦 Installing SpareTools zipapps..."
  bash scripts/install-sparetools-zipapps.sh
fi

# 5. Activate environment
echo "✅ Setup complete!"
echo "Run: source .conan/activate.sh"