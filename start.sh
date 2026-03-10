#!/bin/bash
# Linux/macOS startup script
set -e
cd "$(dirname "$0")/backend"
python run.py
