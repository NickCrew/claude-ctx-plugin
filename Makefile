.PHONY: help install install-dev install-manpage install-completions uninstall test test-cov lint type-check clean docs

# Default target
help:
	@echo "Claude-ctx Development Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install              - Install package, completions, and manpage"
	@echo "  install-dev          - Install in development mode with all dependencies"
	@echo "  install-manpage      - Install manpage only"
	@echo "  install-completions  - Install shell completions only"
	@echo "  uninstall            - Uninstall claude-ctx"
	@echo "  test                 - Run test suite"
	@echo "  test-cov             - Run tests with coverage report"
	@echo "  lint                 - Run code linters (black)"
	@echo "  type-check           - Run mypy type checking"
	@echo "  clean                - Remove build artifacts and caches"
	@echo "  docs                 - Build documentation site"
	@echo ""
	@echo "Examples:"
	@echo "  make install         # Full installation"
	@echo "  make test-cov        # Run tests with coverage"
	@echo "  make type-check      # Check types with mypy"

install:
	@./scripts/install.sh

install-dev:
	@./scripts/install.sh --system-install=false

install-manpage:
	@./scripts/install-manpage.sh

install-completions:
	@./scripts/install.sh --no-package --no-manpage

uninstall:
	@pip uninstall -y claude-ctx-py
	@echo "Note: Manpage and completions must be removed manually"
	@echo "  Manpage: sudo rm /usr/local/share/man/man1/claude-ctx.1"
	@echo "  Bash: rm ~/.local/share/bash-completion/completions/claude-ctx"
	@echo "  Zsh: rm ~/.local/share/zsh/site-functions/_claude-ctx"
	@echo "  Fish: rm ~/.config/fish/completions/claude-ctx.fish"

test:
	@pytest

test-cov:
	@pytest --cov=claude_ctx_py --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "Coverage report: htmlcov/index.html"

lint:
	@black --check claude_ctx_py/
	@echo "✓ Code formatting looks good"

lint-fix:
	@black claude_ctx_py/
	@echo "✓ Code formatted"

type-check:
	@echo "Checking Phase 4 modules (strict)..."
	@mypy claude_ctx_py/activator.py claude_ctx_py/composer.py claude_ctx_py/metrics.py \
	      claude_ctx_py/analytics.py claude_ctx_py/community.py claude_ctx_py/versioner.py \
	      claude_ctx_py/exceptions.py claude_ctx_py/error_utils.py
	@echo "✓ Type checking passed"

type-check-all:
	@echo "Checking all modules (informational)..."
	@mypy claude_ctx_py/ || true

clean:
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info
	@rm -rf .pytest_cache/
	@rm -rf .mypy_cache/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned build artifacts"

docs:
	@cd docs && bundle exec jekyll serve --livereload

verify:
	@echo "=== Verifying Installation ==="
	@command -v claude-ctx >/dev/null 2>&1 && echo "✓ claude-ctx command found" || echo "✗ claude-ctx not found"
	@man -w claude-ctx >/dev/null 2>&1 && echo "✓ manpage installed" || echo "✗ manpage not found"
	@python3 -c "import argcomplete" 2>/dev/null && echo "✓ argcomplete available" || echo "✗ argcomplete not found"
	@echo ""
	@echo "Claude-ctx version:"
	@claude-ctx --help | head -1 || true
