import sys
import threading
import numpy as np
import sounddevice as sd

from tkinter import messagebox

CHUNK_SIZE = 1024           # samples per analysis chunk


def rms_level(signal: np.ndarray) -> float:
    """Root-mean-square level of a signal."""
    return float(np.sqrt(np.mean(np.float64(signal) ** 2)))


def compress(audio, threshold_db=-18.0, ratio=3.0):
    threshold = 10 ** (threshold_db / 20)

    sign = np.sign(audio)
    mag = np.abs(audio).copy()

    over = mag > threshold
    mag[over] = threshold + (mag[over] - threshold) / ratio

    return sign * mag


def normalize(audio, peak=0.99):
    max_peak = np.max(np.abs(audio))
    if max_peak > 0:
        audio = audio * (peak / max_peak)
    return audio

class Recorder:
    """Threaded audio recorder using sounddevice callback."""

    SAMPLE_RATE = 48000
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

        try:
            self._stream = sd.InputStream(
                channels=self.CHANNELS,
                samplerate=self.SAMPLE_RATE,
                callback=callback,
                blocksize=CHUNK_SIZE,
            )
            self._stream.start()
        except sd.PortAudioError as e:
            self._recording = False
            self._stream = None
            messagebox.showerror("No microphone detected.", "The program could not find a microphone, please make sure that it is plugged in and selected.")

            return

    def stop(self) -> tuple[int, np.ndarray]:
        """Stop recording and return (sample_rate, data)."""
        self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if self._buf:
                data = np.concatenate(self._buf, axis=0)[:, 0]
            else:
                data = np.array([], dtype=self.DTYPE)
                
                
        if data.size:
            # Remove DC offset
            data = data - np.mean(data)

            # Compress voice
            data = compress(data, threshold_db=-18, ratio=3.0)

            # Normalize
            data = normalize(data, peak=0.99)



        return self.SAMPLE_RATE, data

    def get_level(self) -> float:
        """Get current mic level (for level meter)."""
        # Read from the most recent buffer chunk
        with self._lock:
            if self._buf:
                return rms_level(self._buf[-1][:, 0])
        return 0.0