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
    parser = argparse.ArgumentParser(
        description="Record voice practice with sentence prompts.",
        epilog="Saves MP3 clips to a 'recordings/' subdirectory, named after each sentence.",
    )
    parser.add_argument("file", nargs="?", help="Text file with one sentence per line")
    args = parser.parse_args()

    sentences_path = args.file
    if not sentences_path:
        # Open file dialog
        sentences_path = filedialog.askopenfilename(
            title="Select sentences file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not sentences_path:
            sys.exit(0)

    if not os.path.isfile(sentences_path):
        print(f"File not found: {sentences_path}", file=sys.stderr)
        sys.exit(1)

    sentences = load_sentences(sentences_path)
    # output_dir = os.path.join(os.path.dirname(os.path.abspath(sentences_path)), "recordings")

    output_dir = os.path.join(read_config("output_dir"), "recordings")


    app = SentenceRecorderApp(sentences, output_dir)
    app.root.mainloop()


if __name__ == "__main__":
    main()
