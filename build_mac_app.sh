#!/bin/bash

# Install necessary dependencies
pip install -r requirements.txt
pip install pyinstaller

# Run PyInstaller to create a Mac app
pyinstaller --onefile --windowed --name "Transcribinator" run_transcription.py

echo "Mac App created! Check the 'dist' folder."
