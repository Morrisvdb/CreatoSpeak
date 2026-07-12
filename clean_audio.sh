#!/bin/bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_folder> <output_folder>"
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"

if [ ! -d "$INPUT_DIR" ]; then
    echo "Input folder does not exist: $INPUT_DIR"
    exit 1
fi

find "$INPUT_DIR" -type f \( \
    -iname "*.wav" -o \
    -iname "*.mp3" -o \
    -iname "*.flac" -o \
    -iname "*.m4a" -o \
    -iname "*.aac" -o \
    -iname "*.ogg" \) | while IFS= read -r input; do

    # Relative path from input directory
    relpath="${input#$INPUT_DIR/}"

    output="$OUTPUT_DIR/$relpath"

    # Create output directory if needed
    mkdir -p "$(dirname "$output")"

    echo "Processing:"
    echo "  $input"
    echo "  -> $output"

    ffmpeg -hide_banner -loglevel warning -y \
        -i "$input" \
        -af "afftdn=nr=8:nf=-40,highpass=f=80,silenceremove=start_periods=1:start_duration=0.15:start_threshold=-45dB:stop_periods=-1:stop_duration=0.15:stop_threshold=-45dB,loudnorm=I=-16:LRA=7:TP=-1.5" \
        -c:a libmp3lame -q:a 0 \
        "$output"

done

echo "Done!"
