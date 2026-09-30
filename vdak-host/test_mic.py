import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

print("Loading Whisper model...")
m = WhisperModel("tiny", device="cpu", compute_type="int8", download_root="models/whisper")

print("\n--- TEST READY ---")
time.sleep(1)
print("3...")
time.sleep(1)
print("2...")
time.sleep(1)
print(">>> 1... SPEAK NOW! <<<")

duration = 5.0
sr = 16000
audio = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype="float32")
sd.wait()

print("\nRecording finished! Processing audio...")
arr = audio.flatten()
max_vol = float(np.max(np.abs(arr)))
print(f"Peak Volume Detected: {max_vol:.4f}")

if max_vol > 0.01:
    arr = arr / max_vol * 0.95

segments, info = m.transcribe(arr, beam_size=1)
text = " ".join([s.text.strip() for s in list(segments)]).strip()

print(f"Detected Language: {info.language} (Confidence: {info.language_probability:.2f})")
print(f"Recognized Text: '{text}'")
