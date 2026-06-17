#!/usr/bin/env python3
"""
Sentence Recorder — a graphical tool for recording voice lines.

Usage:
    python record_sentences.py file.txt

Loads sentences from a text file (one per line), shows them one at a time
while recording microphone audio.
"""

import argparse
import io
import os
import re
import sys
import threading
import unicodedata
import numpy as np
import sounddevice as sd
from pathlib import Path
from pydub import AudioSegment

# try:
HAS_PYDUB = True
# except ImportError:
#     HAS_PYDUB = False

try:
    from tkinter import *
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    print("tkinter is required. Install tk/tkinter for your Python.")
    sys.exit(1)

CHUNK_SIZE = 1024           # samples per analysis chunk


# ── Audio helpers ────────────────────────────────────────────────────────────

def rms_level(signal: np.ndarray) -> float:
    """Root-mean-square level of a signal."""
    return float(np.sqrt(np.mean(np.float64(signal) ** 2)))


def _make_filename(sentence: str) -> str:
    """Create a filesystem-safe filename from sentence text.

    Lowercased, punctuation stripped, whitespace collapsed to single hyphens.
    Max 128 characters.
    """
    # Normalize unicode (e.g. fancy quotes → plain)
    text = unicodedata.normalize("NFKC", sentence)
    # Lowercase
    text = text.lower()
    # Remove punctuation (keep letters, digits, spaces)
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse whitespace
    # text = re.sub(r"\s+", "-", text).strip("-")
    # Truncate to 128 chars
    return text[:128] if text else "recording"


def save_mp3(audio_data: np.ndarray, sample_rate: int) -> bytes:
    """Convert float32 numpy audio to MP3 bytes using pydub."""
    if not HAS_PYDUB:
        # Fallback to WAV
        data_int16 = (audio_data / max(np.max(np.abs(audio_data)), 1e-9) * 32767).astype(np.int16)
        return data_int16.tobytes()
    # Build AudioSegment from raw float32 PCM
    data_int16 = (audio_data / max(np.max(np.abs(audio_data)), 1e-9) * 32767).astype(np.int16)
    seg = AudioSegment(
        data_int16.tobytes(),
        frame_rate=sample_rate,
        channels=1,
        sample_width=2,
    )
    # Export as MP3 in memory
    buf = io.BytesIO()
    seg.export(buf, format="mp3")
    return buf.getvalue()


def sentence_to_filename(sentence: str, max_len: int = 40) -> str:
    """Turn a sentence into a safe short filename stem."""
    stem = sentence.strip().lower()
    stem = unicodedata.normalize("NFKD", stem)
    stem = re.sub(r"[^a-z0-9\s]", "", stem)
    stem = re.sub(r"\s+", " ", stem)
    if len(stem) > max_len:
        stem = stem[: max_len - 3] + "..."
    return stem


def save_mp3_clip(filepath: str, sample_rate: int, audio_data: np.ndarray):
    """Save a single clip as an MP3 file."""
    if not HAS_PYDUB:
        raise RuntimeError("mp3 output requires pydub (pip install pydub)")
    data_int16 = (audio_data / max(np.max(np.abs(audio_data)), 1e-9) * 32767).astype(np.int16)
    seg = AudioSegment(
        data_int16.tobytes(),
        frame_rate=sample_rate,
        channels=1,
        sample_width=2,
    )
    seg.export(filepath, format="mp3")


# ── Recording thread ─────────────────────────────────────────────────────────

class Recorder:
    """Threaded audio recorder using sounddevice callback."""

    SAMPLE_RATE = 44100
    CHANNELS = 1
    DTYPE = np.float32

    def __init__(self, level_callback):
        # level_callback(level: float) -> None   — called from recording thread
        self._level_callback = level_callback
        self._recording = False
        self._buf: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._finished_event = threading.Event()

    def start(self):
        """Start recording. Call from main thread."""
        self._recording = True
        self._buf = []
        self._finished_event.clear()

        def callback(indata, frames, time_info, status):
            if status:
                print(f"Audio callback status: {status}", file=sys.stderr)
            if self._recording:
                level = rms_level(indata[:, 0])
                self._level_callback(level)
                with self._lock:
                    self._buf.append(indata.copy())

        self._stream = sd.InputStream(
            channels=self.CHANNELS,
            samplerate=self.SAMPLE_RATE,
            callback=callback,
            blocksize=CHUNK_SIZE,
        )
        self._stream.start()

    def stop(self) -> tuple[int, np.ndarray]:
        """Stop recording and return (sample_rate, data)."""
        self._recording = False
        self._stream.stop()
        self._stream.close()
        self._stream = None

        with self._lock:
            if self._buf:
                data = np.concatenate(self._buf, axis=0)[:, 0]
            else:
                data = np.array([], dtype=self.DTYPE)

        return self.SAMPLE_RATE, data

    def get_level(self) -> float:
        """Get current mic level (for level meter)."""
        # Read from the most recent buffer chunk
        with self._lock:
            if self._buf:
                return rms_level(self._buf[-1][:, 0])
        return 0.0


# ── GUI Application ──────────────────────────────────────────────────────────

class SentenceRecorderApp:
    def __init__(self, sentences: list[str], output_dir: str):
        self.sentences = sentences
        self.output_dir = output_dir
        self.current_index = 0
        self.audio_clips: list[tuple[int, int, np.ndarray]] = []  # (index, sr, data)
        self.level_meter_value = 0.0

        # Recorder (created when needed)
        self.recorder: Recorder | None = None
        self._level_thread: threading.Thread | None = None

        # Recording state
        self.is_recording = False
        self.has_recorded = False  # whether user has recorded this sentence

        self._build_gui()
        self._show_current()

    # ── GUI Construction ───────────────────────────────────────────────

    def _build_gui(self):
        self.root = Tk()
        self.root.title("Sentence Recorder")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        self.root.configure(bg="#1a1a2e")

        # ── Top frame: progress ──
        top_frame = Frame(self.root, bg="#1a1a2e")
        top_frame.pack(fill=X, padx=20, pady=(15, 5))

        self.progress_label = Label(
            top_frame, text="0 / 0", font=("Helvetica", 12),
            bg="#1a1a2e", fg="#a0a0c0"
        )
        self.progress_label.pack(side=RIGHT)

        self.status_label = Label(
            top_frame, text="Ready — press Record to start",
            font=("Helvetica", 11), bg="#1a1a2e", fg="#7070a0"
        )
        self.status_label.pack(side=LEFT)

        # ── Middle frame: sentence display ──
        mid_frame = Frame(self.root, bg="#1a1a2e")
        mid_frame.pack(expand=True, fill=BOTH, padx=20, pady=(5, 15))

        self.sentence_label = Label(
            mid_frame,
            text="",
            font=("Helvetica", 28, "bold"),
            bg="#1a1a2e",
            fg="#e0e0ff",
            wraplength=700,
            justify=CENTER,
        )
        self.sentence_label.pack(expand=True, fill=BOTH, padx=20, pady=20)

        # ── Level meter ──
        meter_frame = Frame(self.root, bg="#1a1a2e", height=30)
        meter_frame.pack(fill=X, padx=40, pady=(0, 5))
        meter_frame.pack_propagate(False)

        self.meter_bg = Frame(meter_frame, bg="#333355", height=18)
        self.meter_bg.pack(fill=X, expand=True, pady=6)

        self.meter_fill = Frame(self.meter_bg, bg="#00ff88", height=18, width=10)
        self.meter_fill.place(relx=0, rely=0, relwidth=0.0, height=18, anchor="w")

        self.level_text = Label(
            meter_frame, text="No recording", font=("Helvetica", 9),
            bg="#1a1a2e", fg="#505070"
        )
        self.level_text.pack()

        # ── Bottom frame: controls ──
        bottom_frame = Frame(self.root, bg="#1a1a2e")
        bottom_frame.pack(fill=X, padx=20, pady=(5, 15))

        self.record_btn = Button(
            bottom_frame,
            text="⏺  Record",
            font=("Helvetica", 16, "bold"),
            bg="#e74c3c",
            fg="white",
            activebackground="#c0392b",
            activeforeground="white",
            relief=FLAT,
            padx=40,
            pady=12,
            cursor="hand2",
            command=self._toggle_record,
        )
        self.record_btn.pack(side=LEFT)

        self.next_btn = Button(
            bottom_frame,
            text="Next →",
            font=("Helvetica", 13),
            bg="#2980b9",
            fg="white",
            activebackground="#1f6fa3",
            activeforeground="white",
            relief=FLAT,
            padx=25,
            pady=8,
            cursor="hand2",
            state=DISABLED,
            command=self._next_sentence,
        )
        self.next_btn.pack(side=RIGHT)
        
        self.prev_btn = Button(
            bottom_frame,
            text="Previous",
            font=("Helvetica", 13),
            bg="#2980b9",
            fg="white",
            activebackground="#1f6fa3",
            activeforeground="white",
            relief=FLAT,
            padx=25,
            pady=8,
            cursor="hand2",
            state=DISABLED,
            command=self._prev_sentence,
        )
        self.prev_btn.pack(side=LEFT)

        self.save_btn = Button(
            bottom_frame,
            text="Save All",
            font=("Helvetica", 13),
            bg="#27ae60",
            fg="white",
            activebackground="#1e8449",
            activeforeground="white",
            relief=FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
            state=DISABLED,
            command=self._save_all,
        )
        self.save_btn.pack(side=RIGHT, padx=(10, 0))

        # ── Progress dots ──
        self.dots_frame = Frame(self.root, bg="#1a1a2e")
        self.dots_frame.pack(fill=X, padx=20, pady=(5, 15))
        self.dots: list[Label] = []
        self._draw_dots()

        # ── Periodic level update ──
        self._update_level()

        # ── Keyboard shortcuts ──
        self.root.bind("<space>", self._on_space)
        self.root.bind("<Return>", self._on_space)
        self.root.focus_set()

    def _on_space(self, event):
        """Space bar triggers Record or Next depending on state."""
        if self.next_btn['state'] == NORMAL:
            self._next_sentence()
        elif self.is_recording:
            self._toggle_record()
        elif not self.is_recording and self.record_btn['state'] != DISABLED:
            self._toggle_record()

    def _draw_dots(self):
        """Draw dots showing progress through sentences."""
        for w in self.dots:
            w.destroy()
        self.dots = []
        for i, s in enumerate(self.sentences):
            if s.strip():  # skip blank lines
                dot = Label(self.dots_frame, text="●", font=("Helvetica", 10),
                            bg="#1a1a2e", fg="#333355")
                dot.pack(side=LEFT, padx=2)
                self.dots.append(dot)

    def _show_current(self):
        """Show the current sentence and reset controls."""
        sentence = self.sentences[self.current_index]
        self.sentence_label.config(text=sentence if sentence.strip() else "[blank line]")
        self.progress_label.config(text=f"{self.current_index + 1} / {len(self.sentences)}")

        # Update dots
        for i, dot in enumerate(self.dots):
            if i < self.current_index:
                dot.config(fg="#27ae60" if self.has_recorded else "#e67e22")
            elif i == self.current_index:
                dot.config(fg="#e0e0ff")
            else:
                dot.config(fg="#333355")

        # Reset record state
        self.has_recorded = False
        self.next_btn.config(state=DISABLED)
        self._update_status("Press Record to start recording")
        self.level_text.config(text="Press Record to start")
        self.meter_fill.config(width=10, bg="#00ff88")

        # Update record button
        self.record_btn.config(text="⏺  Record", bg="#e74c3c")

    def _update_status(self, msg: str):
        self.status_label.config(text=msg)

    # ── Recording ──────────────────────────────────────────────────────

    def _toggle_record(self):
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self.is_recording = True
        self.record_btn.config(text="⏹  Stop", bg="#34495e")
        self.level_text.config(text="Recording…")

        def on_level(level: float):
            # This runs in the audio callback thread; update GUI via after
            self.root.after(0, self._update_meter, level)

        self.recorder = Recorder(on_level)
        self.recorder.start()

    def _stop_recording(self):
        assert self.recorder is not None
        sr, data = self.recorder.stop()
        self.is_recording = False
        self.recorder = None

        # Store the raw clip
        for clip in self.audio_clips:
            if clip[0] == self.current_index:
                self.audio_clips.remove(clip)        
        self.audio_clips.append((self.current_index, sr, data))
        
        self.has_recorded = True
        self.next_btn.config(state=NORMAL)

        self.record_btn.config(text="⏺  Record", bg="#e74c3c")
        self._update_meter(0)
        self.level_text.config(text="Saved ✓  — press Record again or Next")

        if self.current_index >= len(self.sentences) - 1:
            self.save_btn.config(state=NORMAL)
            self.next_btn.config(state=DISABLED)
            self._update_status("All sentences recorded! Save when ready.")

    def _update_meter(self, level: float):
        # level is RMS ~0.0–1.0; cap at 1.0
        level = min(level * 10, 1.0)  # scale up
        width = int(level * 720)  # meter_bg is ~720px
        self.meter_fill.place(relwidth=0, width=max(10, width), anchor="w")

        # Color based on level
        if level < 0.5:
            self.meter_fill.config(bg="#00ff88")
        elif level < 0.8:
            self.meter_fill.config(bg="#f1c40f")
        else:
            self.meter_fill.config(bg="#e74c3c")

    def _update_level(self):
        """Periodically check mic level for when not actively recording."""
        if self.recorder and self.is_recording:
            pass  # level updated via callback
        self.root.after(100, self._update_level)

    def _next_sentence(self):
        self.current_index += 1
        self.prev_btn.config(state=NORMAL)
        if self.current_index < len(self.sentences):
            self._show_current()
        else:
            self.save_btn.config(state=NORMAL)
            self._update_status("All done! Save your recordings.")

    def _prev_sentence(self):
        if self.current_index > 0:
            self.current_index -= 1
            if self.current_index == 0:
                self.prev_btn.config(state=DISABLED)
            
            if self.current_index < len(self.sentences):
                self.next_btn.config(state=NORMAL)
                
        self._show_current()

    # ── Saving ──── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    def _save_all(self):
        """Save all recorded clips as individual MP3 files, named after each sentence."""
        self._update_status("Saving… please wait…")
        self.root.update()

        os.makedirs(self.output_dir, exist_ok=True)
        saved = 0
            
        print(len(self.audio_clips))
            
        for i, (index, sr, raw_data) in enumerate(self.audio_clips):
            if len(raw_data) == 0:
                continue
            stem = sentence_to_filename(self.sentences[i])
            fname = f"{stem}.mp3"
            fpath = os.path.join(self.output_dir, fname)
            
            # Check if the file already exists
            if os.path.exists(fpath):
                overwrite = messagebox.askyesno(
                    "Duplicate files",
                    f"Warning: There already exists a file with the name {fname} in the output folder. Do you wish to overwite this file?"
                )
                if not overwrite:
                    saved += 1
                    self._update_status(f"Skipped")
                    self.root.update()
                    continue
                    
            
            save_mp3_clip(fpath, sr, raw_data)
            duration = len(raw_data) / sr
            saved += 1
            self._update_status(f"Saved {saved}/{len(self.audio_clips)} — {fname} ({duration:.1f}s)")
            self.root.update()

        messagebox.showinfo(
            "Complete",
            f"Saved {saved} clip(s) to:\n{self.output_dir}",
        )
        # self.save_btn.config(state=DISABLED)
        self._update_status(f"Done! {saved} clips saved.")


# ── Main ─────────────────────────────────────────────────────────────────────

def load_sentences(filepath: str) -> list[str]:
    """Load sentences from a text file, one per line."""
    with open(filepath, "r", encoding="utf-8") as f:
        return [line for line in f.readlines()]


def main():
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
    output_dir = os.path.join(os.path.dirname(os.path.abspath(sentences_path)), "recordings")

    app = SentenceRecorderApp(sentences, output_dir)
    app.root.mainloop()


if __name__ == "__main__":
    main()
