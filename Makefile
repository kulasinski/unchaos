.PHONY: test

test:
	@echo "Running tests..."
	@poetry run pytest

test-ai:
	@echo "Running AI tests..."
	@poetry run pytest tests/ai/test_routine_tasks.py