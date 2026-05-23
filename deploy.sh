#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================="
echo "      ZEROWRITER DEPLOYMENT UTILITY       "
echo "=========================================="

# 1. Sync repository with GitHub
echo "Fetching changes from GitHub..."
git fetch origin
git reset --hard origin/main

# 2. Deploy files
echo "Copying application files..."
# Ensure the examples subdirectory exists
mkdir -p ~/waveshare-python/e-Paper/RaspberryPi_JetsonNano/python/examples/zerowriter

# Copy main.py to examples root
cp main.py ~/waveshare-python/e-Paper/RaspberryPi_JetsonNano/python/examples/

# Copy all python modules to the package directory
cp config.py display.py editor.py file_manager.py keyboard.py sync.py __init__.py ~/waveshare-python/e-Paper/RaspberryPi_JetsonNano/python/examples/zerowriter/

# 3. Restart system service
echo "Restarting Zerowriter service..."
sudo systemctl restart zerowriter.service

echo "=========================================="
echo "   Deployment completed successfully!     "
echo "=========================================="
