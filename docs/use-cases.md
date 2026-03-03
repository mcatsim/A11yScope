# A11yScope Use Cases

## For Instructors

### "I need to make my course ADA compliant before the semester starts"

1. Run A11yScope against your course
2. Focus on **Critical** and **Serious** issues first
3. Use auto-fix for heading hierarchy and table structure
4. Use AI suggestions for alt text on images
5. Download the HTML report to share with your department

### "I'm adding new content and want to check it as I go"

Run A11yScope after adding new modules. The real-time progress shows you exactly which content items have issues, so you can fix them immediately.

### "I have hundreds of images without alt text"

1. Configure an AI provider (Anthropic Claude or OpenAI GPT-4o work great for this)
2. Run the audit
3. Click "AI" on each image issue to get AI-generated alt text suggestions
4. Review and apply the suggestions

---

## For Accessibility Coordinators

### "I need to audit all courses in our department"

Run A11yScope against each course and download JSON reports. The JSON format is machine-readable and can be aggregated with a simple script:

```python
import json, glob
for f in glob.glob("output/*.json"):
    data = json.load(open(f))
    print(f"{data['course_name']}: {data['overall_score']:.1f}%")
```

### "I need VPAT documentation for our institution's accessibility report"

1. Run the audit on each product/course
2. Download the VPAT report (VPAT 2.x WCAG Edition format)
3. The VPAT maps each WCAG criterion to Supports / Partially Supports / Does Not Support
4. Include in your institution's compliance documentation

> **Important**: The VPAT is based on automated scanning only. Supplement with manual testing for a complete assessment.

### "I need to demonstrate Section 508 compliance to our legal team"

The HTML report includes Section 508 provision references alongside WCAG criteria. Each issue maps to specific 508 provisions (e.g., 1194.22(a) for images, 1194.22(d) for tables).

---

## For IT Administrators

### "I want to deploy this for our entire institution"

```bash
# Production Docker deployment
docker compose up --build -d

# With a reverse proxy (Nginx/Caddy recommended)
# A11yScope runs on port 8080 by default
```

For multi-user deployment, consider running behind an SSO-protected reverse proxy. A11yScope is single-user by design (no built-in auth), so institutional SSO provides the access control layer.

### "I want to integrate this into our CI/CD pipeline"

Use the CLI for automated scanning:

```bash
a11yscope audit --course-id 12345 --output json --output-dir reports/
```

Parse the JSON output to fail builds below a threshold:

```bash
score=$(jq '.overall_score' reports/audit_12345.json)
if (( $(echo "$score < 80" | bc -l) )); then
    echo "Accessibility score too low: $score"
    exit 1
fi
```
