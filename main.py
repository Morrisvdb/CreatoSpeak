#!/usr/bin/env python3
"""
Sentence Recorder — a graphical tool for recording voice lines.

Usage:
    python record_sentences.py file.txt

Loads sentences from a text file (one per line), shows them one at a time
while recording microphone audio.
"""

import argparse
import os
import sys

from main_gui import SentenceRecorderApp
from func import load_sentences, config_exists, read_config

try:
    from tkinter import *
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    print("tkinter is required. Install tk/tkinter for your Python.")
    sys.exit(1)


settings_window = None


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    config_exists() # Create a default config file if it does not yet exist
    sentences = None
    if read_config("auto_select_input"):
        input_file = read_config('input_dir')+'/sentences.txt'
        if os.path.exists(input_file):
            sentences = load_sentences(input_file)
        else:
            sentences = None
            
    if sentences is None:
        
        parser = argparse.ArgumentParser(
            description="Record voice practice with sentence prompts.",
            epilog="Saves MP3 clips to a 'recordings/' subdirectory, named after each sentence.",
            
        )
        parser.add_argument("file", nargs="?", help="Text file with one sentence per line")
        args = parser.parse_args()

        sentences_path = args.file
        if not sentences_path:
            input_dir = read_config("input_dir")
            # Open file dialog
            sentences_path = filedialog.askopenfilename(
                title="Select sentences file",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialdir=input_dir
            )
            if not sentences_path:
                sys.exit(0)

        if not os.path.isfile(sentences_path):
            print(f"File not found: {sentences_path}", file=sys.stderr)
            sys.exit(1)

        sentences = load_sentences(sentences_path)
    
    output_dir = os.path.join(read_config("output_dir"), "recordings")


    app = SentenceRecorderApp(sentences, output_dir)
    app.root.mainloop()


if __name__ == "__main__":
    main()
