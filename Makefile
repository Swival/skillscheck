.PHONY: all install test lint format check clean dist

all: check test

install:
	uv sync

test:
	uv run python -m pytest tests/ -v

lint:
	uv run ruff check skillcheck/ tests/

format:
	uv run ruff format skillcheck/ tests/

check: lint
	uv run ruff format --check skillcheck/ tests/

clean:
	rm -rf dist/ __pycache__ skillcheck/__pycache__ tests/__pycache__ .pytest_cache
	find . -name '*.pyc' -delete

dist: clean
	uv build
