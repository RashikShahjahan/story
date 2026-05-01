from mlx_lm import load, generate

model, tokenizer = load("mlx-community/gemma-4-e2b-it-OptiQ-4bit")
response = generate(
    model, tokenizer,
    prompt="Explain quantum computing in simple terms.",
    max_tokens=200,
)
print(response)
