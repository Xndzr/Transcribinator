#!/bin/bash

# Install necessary dependencies
pip install -r requirements.txt
pip install pyinstaller

# Run PyInstaller to create a Mac app
pyinstaller --onefile --windowed --name "Transcribinator" video_transcription_GUI.py

echo "Mac App created! Check the 'dist' folder."
