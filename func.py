import re
import os
import json
from pathlib import Path
import unicodedata
import numpy as np
from pydub import AudioSegment
from platformdirs import PlatformDirs

try:
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    
DEFAULT_CONFIG = {
    "output_dir": str(os.path.join(Path(PlatformDirs("CreatoSpeak").user_documents_path), "CreatoSpeak"))
}
    
    
    
def load_sentences(filepath: str) -> list[str]:
    """Load sentences from a text file, one per line."""
    with open(filepath, "r", encoding="utf-8") as f:
        return [line for line in f.readlines()]


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
    
def config_exists():
    dirs = PlatformDirs("CreatoSpeak")
    config_path = dirs.user_config_dir + "/config.json"
    
    if not os.path.exists(config_path):
        os.makedirs(dirs.user_config_dir, exist_ok=True)        
        with open(config_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        
    return config_path

def reset_default_config():
    path = config_exists()
    os.remove(path=path)

def write_config(key, value):
    path = config_exists()
    
    with open(path, "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            config = {}
        
    # try:
    config[key] = value
    # except ValueError:
    #     return ValueError
    
    print(config)
    with open(path, 'w') as f:
        json.dump(config, f, indent=4)
        
    return True
            
def read_config(key):
    path = config_exists()
    
    with open(path, "r") as f:
        config = json.load(f)
        
    try:
        value = config[key]
    except ValueError:
        return ValueError
    
    return value