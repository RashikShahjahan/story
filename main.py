from mlx_lm import load, generate

model, tokenizer = load("mlx-community/Qwen3.5-9B-OptiQ-4bit")

with open("PROMPT.md", "r") as f:
    prompt = f.read()

user_input = input("Enter your request: ")

response = generate(
    model, tokenizer,
    prompt=prompt + "\n\nUser request: " + user_input,
    max_tokens=200,
)
print(response)
