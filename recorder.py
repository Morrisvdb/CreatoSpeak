import sys
import threading
import numpy as np
import sounddevice as sd

CHUNK_SIZE = 1024           # samples per analysis chunk


def rms_level(signal: np.ndarray) -> float:
    """Root-mean-square level of a signal."""
    return float(np.sqrt(np.mean(np.float64(signal) ** 2)))

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