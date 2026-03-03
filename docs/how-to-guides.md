# How-To Guides

## How to Audit a Course

1. **Configure**: Enter your Canvas URL and API token
2. **Select**: Choose a course from your teaching courses
3. **Audit**: Click "Audit" and watch real-time progress
4. **Review**: Examine issues by severity (Critical → Minor)
5. **Fix**: Apply auto-fixes or use AI suggestions
6. **Report**: Download HTML, VPAT, or JSON reports

## How to Generate a VPAT Report

1. Run a full audit on your course
2. Go to Step 6 (Reports)
3. Click **Download VPAT Report**
4. The report follows VPAT 2.x WCAG Edition format with:
   - Conformance levels per WCAG criterion
   - Grouped by principle (Perceivable, Operable, Understandable, Robust)
   - Automated disclaimer and assessment methodology

## How to Set Up AI Remediation

### Step 1: Choose a Provider

| Provider | Best For | Cost |
|---|---|---|
| Anthropic (Claude) | Alt text, detailed explanations | ~$3/M tokens |
| OpenAI (GPT-4o) | General-purpose suggestions | ~$5/M tokens |
| Google (Gemini) | Budget-friendly, fast | Free tier available |
| Grok (xAI) | Alternative perspective | ~$5/M tokens |

### Step 2: Get an API Key

- **Anthropic**: [console.anthropic.com](https://console.anthropic.com/) → API Keys → Create Key
- **OpenAI**: [platform.openai.com](https://platform.openai.com/) → API Keys → Create new key
- **Google**: [aistudio.google.com](https://aistudio.google.com/) → Get API Key
- **Grok**: [console.x.ai](https://console.x.ai/) → API Keys

### Step 3: Configure

**Option A — Web UI**: Expand "AI Provider (Optional)" in Step 1, select provider, paste key, click Validate.

**Option B — Environment**: Add to `.env`:
```
A11YSCOPE_AI_PROVIDER=anthropic
A11YSCOPE_AI_API_KEY=sk-ant-...
```

### Step 4: Use

After running an audit, click the **AI** button on any issue to get:
- Plain-language explanation of the problem
- Specific fix with example code
- Prevention tips

## How to Fix Common Issues

### Missing Alt Text (Critical)
- **Auto-fix**: Sets `alt=""` (marks as decorative — use only if truly decorative)
- **AI fix**: Generates descriptive alt text using vision API
- **Manual**: Write alt text that describes the image's content and function

### Heading Hierarchy (Serious)
- **Auto-fix**: Normalizes heading levels to remove gaps (h2→h4 becomes h2→h3)
- **Manual**: Restructure content to follow logical heading order

### Missing Table Headers (Serious)
- **Auto-fix**: Adds `scope="col"` to `<th>` elements
- **Manual**: Ensure data tables have proper `<th>` elements for headers

### Color Contrast (Serious)
- **Manual only**: Adjust foreground/background colors to meet WCAG 1.4.3 minimum contrast ratio (4.5:1 for normal text, 3:1 for large text)
- **Tool**: Use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) to verify colors

## How to Add A11yScope to CI/CD

```bash
# In your CI pipeline
pip install a11yscope

# Run audit and export JSON
a11yscope audit --course-id $COURSE_ID --output json --output-dir reports/

# Check score threshold
python3 -c "
import json
with open('reports/latest.json') as f:
    score = json.load(f)['overall_score']
    print(f'Score: {score}')
    exit(0 if score >= 80 else 1)
"
```
