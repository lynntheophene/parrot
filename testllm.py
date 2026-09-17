from llm import LocalLLM


llm = LocalLLM()

text = input("You: hello there! How are you? ")

response = llm.generate(text)

print("LLM:", response)