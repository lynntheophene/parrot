import requests


class LocalLLM:

    def __init__(self):
        self.url = "http://127.0.0.1:8080/v1/chat/completions"

        # Session memory
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful real-time voice assistant. "
                    "Keep responses short, natural, and conversational. "
                    "Usually answer in 1-3 short sentences."
                ),
            }
        ]

        # Keep the last 10 conversation turns
        self.max_turns = 10

    def stream(self, text):

        # Add user's message to session memory
        self.messages.append({
            "role": "user",
            "content": text,
        })

        # Keep system prompt + recent conversation
        self.messages = (
            [self.messages[0]]
            + self.messages[-(self.max_turns * 2):]
        )

        payload = {
            "messages": self.messages,
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

        # Collect the assistant response
        assistant_response = ""

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
                assistant_response += content

                # Stream to your voice agent
                yield content

        # Save complete assistant response to memory
        self.messages.append({
            "role": "assistant",
            "content": assistant_response,
        })

    def generate(self, text):
        return "".join(self.stream(text))

    def clear_memory(self):
        """Clear the current session."""
        self.messages = [self.messages[0]]