# Contributing to Canvas Accessibility Buddy

Thank you for your interest in improving accessibility in education!

## Contributor License Agreement

**Before your first contribution can be merged**, you must agree to our
[Contributor License Agreement (CLA)](CLA.md).

By submitting a pull request, your Git commit signature (name + email) serves
as your electronic signature of the CLA. No separate form is required.

If contributing on behalf of an organization, please have an authorized
representative email matt@catsimanes.com.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Canvas-accessibility-buddy.git
   cd Canvas-accessibility-buddy
   ```
3. Create a virtual environment and install dev dependencies:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev,web,e2e,security]"
   ```
4. Create a feature branch:
   ```bash
   git checkout -b feature/my-improvement
   ```

## Running Tests

```bash
# Unit tests (264 existing)
pytest tests/ --ignore=tests/e2e -v

# E2E tests (web GUI)
pytest tests/e2e/ -v

# Security scan (SAST)
bandit -r src/ -c pyproject.toml
pip-audit
```

## Docker

```bash
docker compose up --build
# Open http://localhost:8080
```

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Add tests for new functionality
- Ensure all existing tests pass
- Follow existing code style
- Write clear commit messages

## Trademark

See [TRADEMARKS.md](TRADEMARKS.md) for our trademark policy. If you fork this
project, you must use a different name.

## License

All contributions are licensed under AGPL-3.0 as described in [LICENSE](LICENSE)
and the [CLA](CLA.md).
