# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code Style

- AVOID inline comments in code!!!

## Commands

### Development Setup
```bash
# Install with development dependencies
pip install -e .[dev]
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_example.py
```

### Code Formatting and Linting
```bash
# Format and lint code (required before commits)
ruff check --fix --select I && ruff format
```

## Architecture Overview

This is a Python package template. Customize this section to describe your package's architecture.

### Testing Strategy

Tests are located in the `tests/` directory. The `conftest.py` provides shared fixtures. Always run tests before committing changes.

### Important Files for Common Tasks

- **Adding new features**: Modify `toolsets/__init__.py` and relevant modules
- **CLI modifications**: Update entry points in `pyproject.toml`
- **Adding dependencies**: Update `pyproject.toml` under `[project.dependencies]` or `[project.optional-dependencies]`

## Issue Resolution Workflow

When given a GitHub issue to solve, follow this workflow:

1. **Create a new branch** named after the issue (e.g., `fix-issue-123` or descriptive name)
2. **Implement the solution** following the existing code patterns and conventions
3. **Run tests** to ensure nothing is broken: `pytest`
4. **Run linting/formatting**: `ruff check --fix --select I && ruff format`
5. That's it. Never use the `git` commit command after a task is finished.

### Git Commands for Issue Workflow
```bash
git checkout -b fix-issue-NUMBER
```

Always ensure tests pass and code is formatted before pushing.
