import requests


class LocalLLM:

    def __init__(self):
        self.url = "http://127.0.0.1:8080/v1/chat/completions"

    def stream(self, text):

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful real-time  hotel receptionist. "
                        "Keep responses short, natural, and conversational. "
                        "Usually answer in 1-3 short sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            "temperature": 0.7,
            "max_tokens": 150,
            "stream": True,
        }

        response = requests.post(
            self.url,
            json=payload,
            stream=True,
            timeout=60,
        )

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            line = line.decode("utf-8")

            if not line.startswith("data:"):
                continue

            data = line[5:].strip()

            if data == "[DONE]":
                break

            try:
                chunk = requests.models.complexjson.loads(data)
            except Exception:
                continue

            choices = chunk.get("choices", [])

            if not choices:
                continue

            delta = choices[0].get("delta", {})

            content = delta.get("content")

            if content:
                yield content

    def generate(self, text):

        return "".join(self.stream(text))