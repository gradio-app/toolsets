# my-package

A Python package template.

> **Note**: Replace `my-package` and `my_package` throughout this repository with your actual package name.

## Installation

This package requires [Python 3.10 or higher](https://www.python.org/downloads/). Install with `pip`:

```bash
pip install my-package
```

or with `uv`:

```bash
uv pip install my-package
```

## Usage

```python
import my_package

# Your code here
```

Replace `my_package` with your actual package name.

## Development

To set up the package for development, clone this repository and run:

```bash
pip install -e ".[dev]"
```

## Testing

Run tests with:

```bash
pytest
```

## Code Formatting

Format code using Ruff:

```bash
ruff check --fix --select I && ruff format
```

## CI/CD Setup

This repository uses GitHub Actions for automated testing and publishing. To enable publishing to PyPI, you need to configure two things:

### 1. GitHub Personal Access Token (GRADIO_PAT)

The `changesets/action` requires a GitHub Personal Access Token to create pull requests and push commits.

**Steps to create and add the token:**

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Name it (e.g., "my-package-ci")
4. Set expiration (or no expiration)
5. Select the following scopes:
   - `repo` (full control of private repositories) — or at minimum:
     - `repo:status`
     - `repo_deployment`
     - `public_repo` (if the repo is public)
     - `workflow` (if you need to trigger workflows)
6. Click "Generate token"
7. Copy the token immediately (you won't see it again)
8. Go to your repository → Settings → Secrets and variables → Actions
9. Click "New repository secret"
10. Name: `GRADIO_PAT`
11. Value: paste the token you created
12. Click "Add secret"

If you're using the `publish` environment, you may also need to add the secret in:
- Settings → Environments → `publish` → Add secret

### 2. PyPI Trusted Publishing (OIDC)

The workflow uses OpenID Connect (OIDC) to authenticate with PyPI, which requires configuring a trusted publisher.

**Steps to add trusted publisher on PyPI:**

1. Go to [PyPI](https://pypi.org) and log in
2. Navigate to Account settings → Manage API tokens → Add a new pending publisher
3. Select **GitHub** as the provider
4. Enter the following information:
   - **Owner**: Your GitHub organization or username (e.g., `your-org` or `your-username`)
   - **Repository name**: Your repository name (e.g., `my-package`)
   - **Workflow filename**: `.github/workflows/publish.yml`
   - **Environment name**: `publish` (since the workflow uses `environment: publish`)
5. Click "Add"

After adding the trusted publisher, the next workflow run should successfully authenticate with PyPI and publish your package.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License
