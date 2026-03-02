# Getting Started with Accessiflow

## Prerequisites

- **Canvas LMS** account with instructor or admin access
- **Canvas API token** (see below)
- **Docker** (recommended) OR **Python 3.12+**

## Step 1: Get Your Canvas API Token

1. Log into your Canvas LMS instance
2. Click your profile picture → **Settings**
3. Scroll down to **Approved Integrations**
4. Click **+ New Access Token**
5. Enter a purpose: "Accessiflow Accessibility Auditor"
6. Leave expiration blank (or set a date)
7. Click **Generate Token**
8. **Copy the token immediately** — you won't see it again!

> **Security note**: Your API token has the same permissions as your Canvas account. Accessiflow only reads course content and optionally writes back fixes. The token is stored locally and never sent to third parties.

## Step 2: Install Accessiflow

### Docker (Easiest)

```bash
git clone https://github.com/mcatsim/Accessiflow.git
cd Accessiflow
cp .env.example .env
```

Edit `.env` and add your Canvas URL and API token:
```
ACCESSIFLOW_CANVAS_BASE_URL=https://canvas.yourschool.edu
ACCESSIFLOW_CANVAS_API_TOKEN=your-token-here
```

Start the application:
```bash
docker compose up --build -d
```

Open http://localhost:8080 in your browser.

### Local Installation

```bash
git clone https://github.com/mcatsim/Accessiflow.git
cd Accessiflow
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[web,ai]"
cp .env.example .env
# Edit .env with your credentials
accessiflow-web
```

## Step 3: Run Your First Audit

1. Open http://localhost:8080
2. Enter your Canvas URL and API token → click **Connect**
3. Select a course from the list
4. Click **Audit [Course Name]**
5. Watch the real-time progress as Accessiflow:
   - Fetches all pages, assignments, discussions, quizzes, and files
   - Runs 21 accessibility checks on HTML content
   - Checks PDFs, Word docs, and PowerPoint files
   - Calculates accessibility scores
6. Review results: issues sorted by severity with WCAG references
7. Apply auto-fixes (heading hierarchy, table scopes)
8. Download reports (HTML, VPAT, JSON)

## Step 4: Configure AI (Optional)

If you want AI-powered remediation suggestions:

1. Get an API key from your preferred provider:
   - [Anthropic Console](https://console.anthropic.com/) (Claude)
   - [OpenAI Platform](https://platform.openai.com/) (GPT-4o)
   - [Google AI Studio](https://aistudio.google.com/) (Gemini)
   - [xAI Console](https://console.x.ai/) (Grok)
2. In the Accessiflow web UI, expand "AI Provider (Optional)"
3. Select your provider, enter your API key, click **Validate Key**
4. Click the **AI** button on any issue to get a remediation suggestion

## Stopping Accessiflow

```bash
docker compose down
```
