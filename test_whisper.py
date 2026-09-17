import whisper
import torch

print("PyTorch:", torch.__version__)
print("ROCm:", torch.version.hip)
print("GPU:", torch.cuda.get_device_name(0))

model = whisper.load_model("base", device="cuda")

print("Whisper loaded on:", next(model.parameters()).device)

result = model.transcribe("test.wav")

print("\nYou said:")
print(result["text"])
