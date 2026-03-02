# Accessiflow

**Open-source accessibility compliance platform for Canvas LMS**

Accessiflow audits your Canvas courses for WCAG 2.1 AA, Section 508, and VPAT compliance — then helps you fix issues with AI-powered remediation suggestions.

![License](https://img.shields.io/badge/license-AGPL--3.0-blue)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Tests](https://img.shields.io/badge/tests-364%20passing-brightgreen)

---

## Why Accessiflow?

| Feature | Blackboard Ally | UDOIT | Pope Tech | Accessiflow |
|---|---|---|---|---|
| Price | $50K+/yr | Free (aging PHP) | Paid SaaS | **Free & open source** |
| AI remediation | No | No | No | **Yes (BYO key)** |
| VPAT reports | No | No | No | **Yes** |
| Triple standard | WCAG only | WCAG only | WCAG only | **WCAG + 508 + VPAT** |
| Self-hosted | No | Yes | No | **Yes** |
| Document checks | Limited | No | No | **PDF, DOCX, PPTX** |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/mcatsim/Accessiflow.git
cd Accessiflow

# Copy and configure environment
cp .env.example .env
# Edit .env with your Canvas URL and API token

# Start Accessiflow
docker compose up --build -d

# Open in browser
open http://localhost:8080
```

### Option 2: Local Development

```bash
# Clone and enter
git clone https://github.com/mcatsim/Accessiflow.git
cd Accessiflow

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install with all extras
pip install -e ".[web,ai,dev]"

# Configure
cp .env.example .env
# Edit .env with your Canvas credentials

# Run
accessiflow-web
# Open http://localhost:8080
```

### Option 3: CLI Only

```bash
pip install -e ".[dev]"
accessiflow audit --course-id 12345
```

---

## Features

### 21 Accessibility Checks

| Category | Checks | Standards |
|---|---|---|
| **Images** | Missing alt text, non-descriptive alt text | WCAG 1.1.1, 508 1194.22(a) |
| **Headings** | Heading hierarchy violations | WCAG 1.3.1, 2.4.6 |
| **Links** | Empty links, non-descriptive link text | WCAG 2.4.4 |
| **Tables** | Missing headers, caption, scope | WCAG 1.3.1, 508 1194.22(d)(g) |
| **Forms** | Missing labels | WCAG 3.3.2, 508 1194.22(n) |
| **Media** | Missing captions, iframe titles | WCAG 1.2.2, 4.1.2 |
| **Color** | Insufficient contrast | WCAG 1.4.3, 508 1194.31(b) |
| **Documents** | PDF tagging/title/language, DOCX alt text, PPTX slide titles | WCAG 1.3.1, 2.4.2, 3.1.1 |
| **Buttons** | Empty buttons, deprecated elements | WCAG 4.1.2 |

### AI-Powered Remediation (Optional)

Bring your own API key from any supported provider:

| Provider | Default Model | Setup |
|---|---|---|
| **Anthropic** | Claude Sonnet | Get key at [console.anthropic.com](https://console.anthropic.com/) |
| **OpenAI** | GPT-4o | Get key at [platform.openai.com](https://platform.openai.com/) |
| **Google** | Gemini 2.0 Flash | Get key at [aistudio.google.com](https://aistudio.google.com/) |
| **Grok** | Grok-3 | Get key at [console.x.ai](https://console.x.ai/) |

AI features include:
- Plain-language issue explanations
- Alt text generation (vision API)
- Link text suggestions
- Remediation guidance

**AI is completely optional.** Accessiflow works fully without any AI provider configured.

### Triple-Standard Reporting

- **WCAG 2.1 AA** — All 50 Level A + AA success criteria mapped
- **Section 508** — Revised Section 508 provisions (incorporates WCAG)
- **VPAT 2.x** — Downloadable Voluntary Product Accessibility Template

### Report Formats

- **HTML Report** — Professional standalone report with score gauges, severity breakdown, standards references, and best-practice links
- **VPAT Report** — VPAT 2.x WCAG Edition format grouped by principle, with conformance levels and disclaimers
- **JSON Report** — Machine-readable for integration with other tools

---

## Architecture

```
src/accessiflow/
├── ai/              # Multi-AI provider abstraction (litellm)
├── canvas/          # Canvas LMS API client, content fetcher/updater
├── checks/          # 21 pluggable accessibility checks
├── remediation/     # Auto-fix engine + AI remediator
├── reporting/       # HTML, VPAT, JSON, console reports
├── scoring/         # Weighted severity scoring (0-100)
├── standards/       # WCAG 2.1, Section 508, VPAT data
├── utils/           # HTML parsing, color utilities
└── web/             # FastAPI web GUI + WebSocket progress
```

### Tech Stack

- **Backend**: Python 3.12+ / FastAPI / Pydantic
- **Frontend**: Alpine.js SPA / PicoCSS
- **AI**: litellm (unified interface for all providers)
- **Documents**: pikepdf (PDF), python-docx (DOCX), python-pptx (PPTX)
- **Reporting**: Jinja2 HTML templates
- **Deployment**: Docker / Docker Compose

---

## Configuration

All settings use the `ACCESSIFLOW_` prefix and can be set via environment variables or `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `ACCESSIFLOW_CANVAS_BASE_URL` | Yes | — | Your Canvas instance URL |
| `ACCESSIFLOW_CANVAS_API_TOKEN` | Yes | — | Canvas API access token |
| `ACCESSIFLOW_OUTPUT_DIR` | No | `output` | Directory for report files |
| `ACCESSIFLOW_MAX_FILE_SIZE_MB` | No | `50` | Max file size to check |
| `ACCESSIFLOW_AI_PROVIDER` | No | — | AI provider: anthropic, openai, google, grok |
| `ACCESSIFLOW_AI_API_KEY` | No | — | API key for AI provider |
| `ACCESSIFLOW_AI_MODEL` | No | — | Override default AI model |

### Getting a Canvas API Token

1. Log into Canvas as an instructor or admin
2. Go to **Account → Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Give it a name (e.g., "Accessiflow") and click **Generate Token**
6. Copy the token — you won't see it again

---

## API Reference

### Canvas Configuration
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/config` | Validate Canvas credentials |
| GET | `/api/config/status` | Check authentication status |

### Courses
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/courses` | List teacher's courses |

### Audit
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/audit` | Start accessibility audit |
| GET | `/api/audit/{job_id}` | Get audit status/results |
| WS | `/ws/audit/{job_id}` | Real-time progress stream |

### Fix & Remediate
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/fix/{job_id}` | Apply auto-fixes |

### AI (Optional)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/ai/config` | Configure AI provider |
| GET | `/api/ai/config/status` | AI configuration status |
| GET | `/api/ai/providers` | List available providers |
| POST | `/api/ai/suggest/{job_id}` | Get AI suggestion for issue |
| POST | `/api/ai/suggest-batch/{job_id}` | Bulk AI suggestions |

### Reports
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/report/{job_id}/html` | Download HTML report |
| GET | `/api/report/{job_id}/json` | Download JSON report |
| GET | `/api/report/{job_id}/vpat` | Download VPAT report |

---

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev,web,ai]"

# Run all tests
pytest tests/ -v

# Run with coverage
coverage run -m pytest tests/ -v
coverage report
```

### Test Structure

| File | Tests | Coverage |
|---|---|---|
| `test_standards.py` | 30 | WCAG criteria, 508 provisions, mappings |
| `test_html_checks.py` | 50+ | All 13 HTML accessibility checks |
| `test_models.py` | 23 | Pydantic models and computed fields |
| `test_scoring.py` | 20+ | Weighted scoring engine |
| `test_media_checks.py` | 19 | PDF, DOCX, PPTX, image checks |
| `test_ai_providers.py` | 10 | AI provider abstraction |
| `test_ai_remediator.py` | 5 | AI remediation suggestions |
| `test_vpat_report.py` | 5 | VPAT report generation |
| `test_autofix.py` | 15+ | Heading, scope, alt text fixes |
| `e2e/test_ai_routes.py` | 5 | AI API endpoints |
| `e2e/test_vpat_download.py` | 3 | VPAT/HTML report downloads |
| `e2e/test_health.py` | 3 | Health endpoint |
| **Total** | **364** | |

### Adding a New Check

1. Create a class in `checks/` extending `AccessibilityCheck`
2. Decorate with `@register_check`
3. Add standards mapping in `standards/mapping.py`
4. Add tests in `tests/`

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and pull request process.

---

## License

AGPL-3.0-only — See [LICENSE](LICENSE) for details.

**Business model**: Open source core + professional consulting services for accessibility compliance programs.
