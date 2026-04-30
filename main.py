from mlx_lm import load, stream_generate

model, tokenizer = load("mlx-community/Qwen3.5-9B-OptiQ-4bit")

with open("PROMPT.md", "r") as f:
    prompt = f.read()

user_input = input("Enter your request: ")

for chunk in stream_generate(
    model, tokenizer,
    prompt=prompt + "\n\nUser request: " + user_input,
    max_tokens=128000,
):
    print(chunk.text, end="", flush=True)
