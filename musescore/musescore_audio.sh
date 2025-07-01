#!/bin/bash

# Path to your MuseScore AppImage
MUSESCORE_PATH="MuseScore-Studio-4.4.4.243461245-x86_64.AppImage"
# MUSESCORE_PATH="/home/vic/Downloads/MuseScore-Studio-4.4.4.243461245-x86_64.AppImage"

# Check if an input file path is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_input_mscz_file>"
    echo "Example: $0 /home/vic/Desktop/tfg/musescore/my_score.mscz"
    exit 1
fi

# Input MSCZ file (taken from the first command-line argument)
INPUT_MSCZ_FILE="$1"

# # Input MSCZ file (full path as provided)
# INPUT_MSCZ_FILE="/home/vic/Desktop/tfg/musescore/seleection.mscz"

# Output directory for WAV files (full path as provided)
OUTPUT_DIR="musescore/out"
# OUTPUT_DIR="/home/vic/Desktop/tfg/musescore/out"

# Base name for the output files (without extension)
OUTPUT_BASENAME=$(basename "$INPUT_MSCZ_FILE" .mscz)

# Temporary WAV file from MuseScore (before trimming)
TEMP_WAV_FILE="$OUTPUT_DIR/${OUTPUT_BASENAME}_temp.wav"

# Final trimmed WAV file
FINAL_WAV_FILE="$OUTPUT_DIR/${OUTPUT_BASENAME}.wav"

# Duration to remove from the end (in seconds)
TRIM_SECONDS=3

# Make the AppImage executable if it's not already
chmod +x "$MUSESCORE_PATH"

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "Converting $INPUT_MSCZ_FILE to temporary WAV using MuseScore..."

# Step 1: Export to WAV using MuseScore
"$MUSESCORE_PATH" "$INPUT_MSCZ_FILE" -o "$TEMP_WAV_FILE"

if [ $? -eq 0 ]; then
    echo "MuseScore export successful. Now trimming the last $TRIM_SECONDS seconds with FFmpeg..."

    # Check if FFmpeg is installed before attempting to use it
    if ! command -v ffmpeg &> /dev/null
    then
        echo "Error: FFmpeg is not installed. Please install FFmpeg to trim the audio."
        echo "For Debian/Ubuntu: sudo apt install ffmpeg"
        echo "For Fedora: sudo dnf install ffmpeg"
        echo "For Arch Linux: sudo pacman -S ffmpeg"
        exit 1
    fi

    # Step 2: Trim the last N seconds using FFmpeg
    # First, get the duration of the temporary WAV file
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$TEMP_WAV_FILE")

    # Calculate the new desired duration
    NEW_DURATION=$(echo "$DURATION - $TRIM_SECONDS" | bc -l)

    # Ensure the new duration is not negative
    if (( $(echo "$NEW_DURATION < 0" | bc -l) )); then
        echo "Warning: The file is shorter than $TRIM_SECONDS seconds. Will not trim or will result in an empty file."
        # Optionally, just copy the original if it's too short
        cp "$TEMP_WAV_FILE" "$FINAL_WAV_FILE"
        rm "$TEMP_WAV_FILE"
        exit 0
    fi

    # Use FFmpeg to cut the audio to the calculated new duration
    # -ss 0: start from the beginning
    # -t $NEW_DURATION: set the output duration
    # -y: overwrite output file without asking
    ffmpeg -i "$TEMP_WAV_FILE" -ss 0 -t "$NEW_DURATION" -y "$FINAL_WAV_FILE"

    if [ $? -eq 0 ]; then
        echo "Last $TRIM_SECONDS seconds trimmed successfully! Final WAV file saved to: $FINAL_WAV_FILE"
        # Optional: Remove the temporary file
        rm "$TEMP_WAV_FILE"
    else
        echo "Error during FFmpeg trimming. Check FFmpeg output above for details."
    fi
else
    echo "Error during MuseScore export. Check MuseScore output above for details."
fi