# Frequently Asked Questions

## General

### What accessibility standards does Accessiflow check?
Accessiflow checks against three standards:
- **WCAG 2.1 Level A and AA** — 50 success criteria mapped
- **Section 508** (Revised) — provisions mapped to WCAG
- **VPAT 2.x** — automated conformance assessment

### What content types does Accessiflow check?
- **HTML content**: Pages, Assignments, Discussions, Announcements, Syllabus, Quizzes
- **Documents**: PDF (tagging, title, language, image-only), DOCX (image alt text), PPTX (slide titles)
- **Images**: Standalone image files (JPG, PNG, GIF, SVG)
- **Media**: Video/audio embeds, iframes (caption and title detection)

### How accurate is automated accessibility testing?
Automated tools typically detect 30-40% of accessibility issues. Accessiflow is excellent for catching structural issues (missing alt text, heading problems, table structure, color contrast) but cannot replace manual testing for:
- Meaningful alt text quality
- Reading order correctness
- Keyboard navigation
- Screen reader compatibility
- Cognitive accessibility

**Best practice**: Use Accessiflow as your first pass, then supplement with manual review.

### Is Accessiflow free?
Yes! Accessiflow is open source under the AGPL-3.0 license. You can:
- Use it for free at your institution
- Modify the code to fit your needs
- Contribute improvements back to the community

AI features require a BYO API key, which has its own costs from the provider.

---

## Setup & Configuration

### How do I get a Canvas API token?
Go to Canvas → Account → Settings → Approved Integrations → + New Access Token. See the [Getting Started guide](getting-started.md) for detailed steps.

### What permissions does the Canvas API token need?
The token inherits your Canvas user permissions. Accessiflow needs:
- **Read access** to course content (pages, assignments, discussions, files)
- **Write access** (optional) only if you want to push auto-fixes back to Canvas

An instructor-level token is sufficient for auditing your own courses.

### Can I use Accessiflow without Docker?
Yes! Install with `pip install -e ".[web,ai]"` in a Python 3.12+ virtual environment and run `accessiflow-web`. See the [Getting Started guide](getting-started.md).

### How do I configure AI features?
1. Get an API key from Anthropic, OpenAI, Google, or xAI
2. Either set `ACCESSIFLOW_AI_PROVIDER` and `ACCESSIFLOW_AI_API_KEY` in `.env`, or configure in the web UI under "AI Provider (Optional)"
3. AI is completely optional — all core features work without it

---

## Usage

### What does the accessibility score mean?
The score (0-100) is a weighted average based on issue severity:
- **Critical** issues: 10 weight points
- **Serious** issues: 5 weight points
- **Moderate** issues: 3 weight points
- **Minor** issues: 1 weight point

A score of 90+ is considered "Passing." The score is per-item and per-course.

### What's the difference between auto-fixable and AI-fixable?
- **Auto-fixable** (gear icon): Deterministic fixes that Accessiflow applies automatically — heading hierarchy normalization, table scope attributes
- **AI-fixable** (star icon): Issues where AI can suggest improvements — alt text, link text, issue explanations
- **Manual** (dash): Issues requiring human judgment — ensuring alt text is meaningful, video captions are accurate

### Can Accessiflow push fixes back to Canvas?
Yes! When applying fixes, check "Push fixes to Canvas" to write the corrected HTML back to your course. Only auto-fixes are pushed — AI suggestions are advisory.

### How long does an audit take?
Depends on course size. A typical course (20-50 content items, 10-20 files) takes 1-3 minutes. The web UI shows real-time progress via WebSocket.

---

## Troubleshooting

### "Connection failed" when entering Canvas credentials
- Verify your Canvas URL is correct (include `https://`)
- Check that your API token is valid (not expired)
- Ensure your Canvas instance allows API access

### "Rate limited" errors during audit
Accessiflow respects Canvas API rate limits (250ms between requests, exponential backoff on 429). If you're still getting rate limited, try running during off-peak hours.

### Docker container won't start
```bash
# Check logs
docker compose logs

# Rebuild
docker compose down
docker compose up --build
```

### Tests are failing
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Install all dev dependencies
pip install -e ".[web,ai,dev,e2e]"

# Run tests
pytest tests/ -v --tb=long
```
