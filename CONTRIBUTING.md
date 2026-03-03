# Contributing to A11yScope

Thank you for your interest in making Canvas LMS more accessible! Here's how to get involved.

## Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR-USERNAME/A11yScope.git
cd A11yScope

# Create virtual environment (Python 3.12+ required)
python3.12 -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install -e ".[web,ai,dev,e2e,security]"

# Run tests to verify setup
pytest tests/ -v
```

## Project Structure

```
src/a11yscope/
├── ai/           # AI providers (litellm abstraction)
├── canvas/       # Canvas LMS API client
├── checks/       # Pluggable accessibility checks
├── remediation/  # Auto-fix and AI remediation
├── reporting/    # Report generators (HTML, VPAT, JSON)
├── scoring/      # Weighted scoring engine
├── standards/    # WCAG 2.1, Section 508, VPAT data
├── utils/        # HTML/CSS parsing helpers
└── web/          # FastAPI app + Alpine.js frontend
```

## Adding a New Accessibility Check

1. **Create the check class** in `src/a11yscope/checks/`:

```python
from a11yscope.checks.base import AccessibilityCheck
from a11yscope.checks.registry import register_check
from a11yscope.models import Severity

@register_check
class MyNewCheck(AccessibilityCheck):
    check_id = "my-new-check"
    title = "My New Check"
    description = "Description of what this checks"
    wcag_criterion = "1.3.1"  # WCAG criterion ID

    def check_html(self, html: str, url: str) -> list:
        issues = []
        # Your check logic here
        return issues
```

2. **Add standards mapping** in `src/a11yscope/standards/mapping.py`:

```python
"my-new-check": StandardsMapping(
    wcag_criteria=("1.3.1",),
    section_508_provisions=("E205.4",),
    best_practice_urls=("https://www.w3.org/WAI/tutorials/...",),
),
```

3. **Write tests** in `tests/test_my_check.py`

4. **Run the full suite**: `pytest tests/ -v`

## Code Style

- Python 3.12+ syntax (but use `from __future__ import annotations` in new files)
- Type hints on all public functions
- Docstrings on all public classes and functions
- No external dependencies without discussion — keep the stack minimal

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-check`)
3. Write tests first (TDD encouraged)
4. Implement the feature
5. Run `pytest tests/ -v` — all tests must pass
6. Run `bandit -r src/` — no security issues
7. Submit a PR with a clear description

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include Canvas LMS version, Python version, and browser (for web GUI issues)
- For accessibility issues in A11yScope itself, please file an issue — we eat our own dog food

## License

By contributing, you agree that your contributions will be licensed under the AGPL-3.0 license.
