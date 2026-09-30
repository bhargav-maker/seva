import time
from voice.asr import ASREngine

print("Initializing ASR Engine...")
asr = ASREngine()

print("\nGet ready to speak in:")
for i in [3, 2, 1]:
    print(f"{i}...")
    time.sleep(1)

print(">>> SPEAK NOW! <<<")
result = asr.listen_and_transcribe(duration=4.0)

print("\n-------------------------")
print(f"Recognized: '{result}'")
print("-------------------------")
