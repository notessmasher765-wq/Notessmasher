#!/usr/bin/env bash
set -e

echo "Starting Render build..."



# Upgrade pip
python3 -m pip install --upgrade pip

# Install all Python dependencies from requirements.txt
python3 -m pip install -r requirements.txt

# Make sure gunicorn is installed in the runtime
python3 -m pip install gunicorn

echo "Render build finished successfully!"
