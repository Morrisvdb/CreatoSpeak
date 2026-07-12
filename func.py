import re
import os
import json
import tempfile
from pathlib import Path
import unicodedata
import numpy as np
from pydub import AudioSegment
from platformdirs import PlatformDirs

from tkinter import messagebox, Toplevel, Label, Button

try:
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    
DEFAULT_CONFIG = {
    "output_dir": str(os.path.join(Path(PlatformDirs("CreatoSpeak").user_documents_path), "CreatoSpeak")),
    "input_dir": str(os.path.join(Path(PlatformDirs("CreatoSpeak").user_documents_path), "CreatoSpeak")),
    "temp_dir": str(tempfile.gettempdir()),
    "auto_select_input": False,
    "denoise_audio": True,
    "autosave": True,
    "save_on_close": True
}

def messageWindow(title, message, options: list):
    if len(options) < 1:
        return
    win = Toplevel()
    win.title('warning')
    message = "This will delete stuff"
    Label(win, text=message).pack()
    for option in options:
        Button(win, text=option, command=...).pack()
        
    
def load_sentences(filepath: str) -> list[str]:
    """Load sentences from a text file, one per line."""
    
    if filepath.endswith(('.vocab', '.sentences')):
        if filepath.endswith(".vocab"):
            vocab = read_vocab(filepath)
            words = vocab[0]
            langs = vocab[1]
            
            dest_lang = messagebox.askyesno("Language automatically selected.", f"The target language has been automatically set to {langs[0]}. Is this correct?")
            if not dest_lang:
                lst = [word[1] for word in words]                
                lst = remove_duplicates(lst)
                return lst
            elif dest_lang:
                lst = [word[0] for word in words]
                
                lst = remove_duplicates(lst)
                return lst
        
        elif filepath.endswith(".sentences"):
            sentences = read_sentences(filepath)
            swap = messagebox.askyesno("Order of translations.", "Should the origin and translations be swapped?")
            if swap:
                return sentences[0][1]
            else:
                return sentences[0][0]
            
            
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            return [line for line in f.readlines()]
    
def remove_duplicates(lst: list):
    if len(lst) > len(set(lst)):
        remove = messagebox.askyesno("Duplicates detected.", "Duplicate entries were found in the target language, should these be removed?")
        if remove:
            return list(dict.fromkeys(lst))
        else:
            return lst
    return lst


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
    do_denoise = read_config("denoise_audio")
    if do_denoise:
        temp_dir = read_config("temp_dir")
    
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
    
    # TODO: Implement noise filtering
        
            
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
        
    config[key] = value
    
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

def read_vocab(path):
    vocab_list = []
    lang_origin = None
    lang_dest = None
    
    with open(path, "r") as vocab_file:
        langs = vocab_file.readline()
        if re.match("<Legend:\\{[A-Za-z]+\\}\\{[A-Za-z]+\\}>", langs):
            langs = langs.removeprefix("<Legend:{").removesuffix("}>")
            
            
            lang_origin = langs.split("}{")[0]
            lang_dest = langs.split("}{")[1]
            
        for line in vocab_file.readlines():
            if not re.match("<\\{[^}]*\\}\\{[^}]*\\}>", line):
                break
            
            pair = line[:-3][2:]
            pair = pair.split("}{")
            
            vocab_list.append(pair)
            
        # vocab_list.pop(0)
            
    return vocab_list, (lang_origin, lang_dest)

def read_sentences(path):
    sentences_list = []
    translations_list = []
    order = None # 0: Sentence|Translation, 1: Translation|Sentence
    
    with open(path, "r") as sentence_file:
        header = sentence_file.readline()
        if re.match("^[a-zA-Z0-9_ ]+\\|[a-zA-Z0-9_ ]+", header):
            if header.split("|")[0].lower() == "sentence":
                order = 0
            elif header.split("|")[0].lower() == "translation":
                order = 1
            
        lines = sentence_file.readlines()
        # lines.pop(0)
        for line in lines:
            if not re.match("^[a-zA-Z0-9_ ]+\\|[a-zA-Z0-9_ ]+", line):
                break
            
            sentences_list.append(line.split('|')[order])
            translations_list.append(line.split('|')[1 if order == 0 else 0])
            
    
    return (sentences_list, translations_list), order