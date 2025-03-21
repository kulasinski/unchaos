.PHONY: test

ollama-pull:
	@echo "Pulling Ollama models..."
	@ollama pull llama3.2:3b
	@ollama pull qwen2.5:14b
	@ollama pull nomic-embed-text

test:
	@echo "Running tests..."
	@poetry run pytest

test-ai:
	@echo "Running AI tests..."
	@poetry run pytest tests/ai/test_routine_tasks.py