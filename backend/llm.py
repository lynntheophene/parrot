import requests
import json


class LocalLLM:

    def __init__(self):

        self.url = (
            "http://127.0.0.1:8080/v1/chat/completions"
        )

        self.system_prompt = (
            "You are a helpful real-time voice assistant. "
            "Keep responses short, natural, and conversational. "
            "Usually answer in 1-3 short sentences. "
            "You have access to the entire conversation history "
            "in this session. Use it when answering questions "
            "about previous messages."
        )

        self.messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        self.max_turns = 20

    def stream(self, text):

        # Add user message
        self.messages.append({
            "role": "user",
            "content": text,
        })

        # Keep:
        # system prompt
        # + last 10 user/assistant turns
        self.messages = (
            [self.messages[0]]
            + self.messages[-(self.max_turns * 2):]
        )

        payload = {
            "messages": self.messages,
            "temperature": 0.7,
            "max_tokens": 200,
            "stream": True,
        }

        response = requests.post(
            self.url,
            json=payload,
            stream=True,
            timeout=60,
        )

        response.raise_for_status()

        assistant_response = ""

        for line in response.iter_lines():

            if not line:
                continue

            if isinstance(line, bytes):
                line = line.decode("utf-8")

            if not line.startswith("data:"):
                continue

            data = line[5:].strip()

            if data == "[DONE]":
                break

            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            choices = chunk.get(
                "choices",
                []
            )

            if not choices:
                continue

            delta = choices[0].get(
                "delta",
                {}
            )

            content = delta.get(
                "content"
            )

            if content:

                assistant_response += content

                yield content

        # IMPORTANT:
        # Save the complete response
        # into this session's memory.

        self.messages.append({
            "role": "assistant",
            "content": assistant_response,
        })

    def generate(self, text):

        return "".join(
            self.stream(text)
        )

    def clear_memory(self):

        self.messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

    def get_history(self):

        return self.messages.copy()