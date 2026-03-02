/**
 * Accessiflow — Alpine.js SPA
 */
function auditApp() {
  return {
    // Wizard state
    step: 1,
    stepLabels: ['Configure', 'Select Course', 'Audit', 'Results', 'Fix', 'Reports'],

    // Step 1: Config
    canvasUrl: 'https://canvas.jccc.edu',
    apiToken: '',
    connecting: false,
    validated: false,
    configError: '',
    userName: '',

    // Step 2: Courses
    courses: [],
    courseFilter: '',
    loadingCourses: false,
    selectedCourse: null,

    // Step 3: Audit progress
    jobId: null,
    progressLog: [],
    currentPhaseLabel: '',
    progressPct: 0,
    ws: null,

    // Step 4: Results
    result: null,

    // Step 5: Fix
    selectedFixes: [],
    pushToCanvas: false,
    fixing: false,
    fixResult: null,

    // AI config
    aiProvider: '',
    aiApiKey: '',
    aiModel: '',
    aiValidating: false,
    aiValidated: false,
    aiError: '',
    aiSuggestions: {},

    // Course metadata
    courseMeta: null,

    async init() {
      // Check if already configured (page reload)
      try {
        const resp = await fetch('/api/config/status');
        const data = await resp.json();
        if (data.validated) {
          this.validated = true;
          this.userName = data.user_name;
          this.canvasUrl = data.canvas_base_url;
        }
      } catch (e) {
        // ignore
      }
    },

    // ─── Step 1: Connect ─────────────────────────────────────
    async connect() {
      this.connecting = true;
      this.configError = '';
      try {
        const resp = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            canvas_base_url: this.canvasUrl,
            canvas_api_token: this.apiToken,
          }),
        });
        const data = await resp.json();
        if (data.ok) {
          this.validated = true;
          this.userName = data.user_name;
          await this.loadCourses();
          this.step = 2;
        } else {
          this.configError = data.error || 'Connection failed';
        }
      } catch (e) {
        this.configError = 'Network error: ' + e.message;
      } finally {
        this.connecting = false;
      }
    },

    // ─── AI Validation ──────────────────────────────────────
    async validateAI() {
      this.aiValidating = true;
      this.aiError = '';
      try {
        const resp = await fetch('/api/ai/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: this.aiProvider,
            api_key: this.aiApiKey,
            model: this.aiModel,
          }),
        });
        const data = await resp.json();
        if (data.ok) {
          this.aiValidated = true;
          this.aiModel = data.model;
        } else {
          this.aiError = data.error || 'Validation failed';
        }
      } catch (e) {
        this.aiError = 'Network error: ' + e.message;
      } finally {
        this.aiValidating = false;
      }
    },

    // ─── Step 2: Load Courses ────────────────────────────────
    async loadCourses() {
      this.loadingCourses = true;
      try {
        const resp = await fetch('/api/courses');
        this.courses = await resp.json();
      } catch (e) {
        this.configError = 'Failed to load courses';
      } finally {
        this.loadingCourses = false;
      }
    },

    filteredCourses() {
      if (!this.courseFilter) return this.courses;
      const q = this.courseFilter.toLowerCase();
      return this.courses.filter(
        c => c.name.toLowerCase().includes(q) || c.course_code.toLowerCase().includes(q)
      );
    },

    // ─── Step 3: Start Audit ─────────────────────────────────
    async startAudit() {
      this.step = 3;
      this.progressLog = [];
      this.progressPct = 0;
      this.currentPhaseLabel = 'Starting audit...';
      this.result = null;
      this.fixResult = null;
      this.selectedFixes = [];

      try {
        const resp = await fetch('/api/audit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ course_id: this.selectedCourse.id }),
        });
        const data = await resp.json();
        this.jobId = data.job_id;
        this.connectWs();
      } catch (e) {
        this.progressLog.push({ type: 'error', message: 'Failed to start audit: ' + e.message });
      }
    },

    connectWs() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      this.ws = new WebSocket(`${proto}://${location.host}/ws/audit/${this.jobId}`);

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        this.progressLog.push(msg);
        this.handleProgress(msg);
      };

      this.ws.onclose = () => {
        // If we didn't get a "complete" message, poll for status
        if (this.step === 3 && !this.result) {
          setTimeout(() => this.pollStatus(), 1000);
        }
      };

      this.ws.onerror = () => {
        // Fall back to polling
        setTimeout(() => this.pollStatus(), 1000);
      };
    },

    handleProgress(msg) {
      switch (msg.type) {
        case 'phase':
          this.currentPhaseLabel = msg.label;
          const phases = { fetching: 10, checking: 40, files: 70, scoring: 90 };
          this.progressPct = phases[msg.phase] || this.progressPct;
          break;
        case 'item_found':
          break;
        case 'item_checked':
          if (msg.total > 0) {
            this.progressPct = 40 + (msg.checked / msg.total) * 30;
          }
          break;
        case 'file_checked':
          break;
        case 'complete':
          this.progressPct = 100;
          this.currentPhaseLabel = `Complete — Score: ${msg.score?.toFixed(1)}%`;
          this.loadResult();
          break;
        case 'error':
          this.currentPhaseLabel = 'Error: ' + msg.message;
          break;
      }
    },

    async pollStatus() {
      if (!this.jobId) return;
      try {
        const resp = await fetch(`/api/audit/${this.jobId}`);
        const data = await resp.json();
        if (data.status === 'complete' && data.result) {
          this.result = data.result;
          this.progressPct = 100;
          this.step = 4;
        } else if (data.status === 'failed') {
          this.currentPhaseLabel = 'Failed: ' + (data.error || 'Unknown error');
        } else if (data.status === 'running') {
          // Keep polling
          setTimeout(() => this.pollStatus(), 2000);
        }
      } catch (e) {
        // retry
        setTimeout(() => this.pollStatus(), 3000);
      }
    },

    async loadResult() {
      try {
        const resp = await fetch(`/api/audit/${this.jobId}`);
        const data = await resp.json();
        if (data.result) {
          this.result = data.result;
          this.step = 4;
        }
      } catch (e) {
        // fallback: stay on step 3 and poll
        setTimeout(() => this.pollStatus(), 2000);
      }
    },

    // ─── Step 4: Results helpers ─────────────────────────────
    scoreClass(score) {
      if (score == null) return '';
      if (score >= 90) return 'sc-pass';
      if (score >= 70) return 'sc-warn';
      return 'sc-fail';
    },

    getStandards(issue) {
      // Map check IDs to their primary standards references
      const map = {
        'alt-text-missing': '508: 1194.22(a)',
        'alt-text-nondescriptive': '508: 1194.22(a)',
        'heading-hierarchy': 'WCAG 2.4.6',
        'table-missing-headers': '508: 1194.22(d)',
        'table-header-missing-scope': '508: 1194.22(g)',
        'media-missing-captions': '508: 1194.22(b)',
        'form-input-missing-label': '508: 1194.22(n)',
        'color-contrast': '508: 1194.31(b)',
        'pdf-not-tagged': '508: E205.4',
        'pdf-missing-title': '508: E205.4',
        'pdf-missing-language': '508: E205.4',
      };
      return map[issue.check_id] || '';
    },

    sortedContent() {
      if (!this.result?.content_items) return [];
      return [...this.result.content_items].sort((a, b) => (a.score ?? 999) - (b.score ?? 999));
    },

    sortedFiles() {
      if (!this.result?.file_items) return [];
      return [...this.result.file_items].sort((a, b) => (a.score ?? 999) - (b.score ?? 999));
    },

    allIssues() {
      if (!this.result) return [];
      const issues = [];
      for (const item of (this.result.content_items || [])) {
        for (const iss of item.issues) {
          issues.push({ ...iss, _itemName: item.title });
        }
      }
      for (const item of (this.result.file_items || [])) {
        for (const iss of item.issues) {
          issues.push({ ...iss, _itemName: item.display_name });
        }
      }
      const order = { critical: 0, serious: 1, moderate: 2, minor: 3 };
      issues.sort((a, b) => (order[a.severity] ?? 99) - (order[b.severity] ?? 99));
      return issues;
    },

    hasFixableIssues() {
      return this.allIssues().some(i => i.auto_fixable && !i.fixed);
    },

    // ─── Step 5: Fix ─────────────────────────────────────────
    fixableIssues() {
      return this.allIssues().filter(i => i.auto_fixable && !i.fixed);
    },

    async applyFixes() {
      this.fixing = true;
      this.fixResult = null;
      try {
        const resp = await fetch(`/api/fix/${this.jobId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            issue_indices: this.selectedFixes.map(Number),
            push_to_canvas: this.pushToCanvas,
          }),
        });
        this.fixResult = await resp.json();
        // Reload result to get updated scores
        await this.loadResult();
      } catch (e) {
        this.fixResult = { fixed_count: 0, errors: ['Request failed: ' + e.message] };
      } finally {
        this.fixing = false;
      }
    },

    // ─── AI Suggestion ─────────────────────────────────────
    async getAISuggestion(issueIdx) {
      const issues = this.allIssues();
      if (issueIdx >= issues.length) return;
      issues[issueIdx]._aiLoading = true;
      try {
        const resp = await fetch(`/api/ai/suggest/${this.jobId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ issue_index: issueIdx }),
        });
        const data = await resp.json();
        if (data.error) {
          alert('AI error: ' + data.error);
        } else {
          this.aiSuggestions[issueIdx] = data;
          alert('AI Suggestion:\n\n' + data.explanation);
        }
      } catch (e) {
        alert('Failed to get AI suggestion: ' + e.message);
      } finally {
        issues[issueIdx]._aiLoading = false;
      }
    },

    // ─── Step 3: Log formatting ──────────────────────────────
    formatLogEntry(entry) {
      switch (entry.type) {
        case 'phase': return entry.label;
        case 'item_found': return entry.label;
        case 'item_checked': return `Checked: ${entry.title} (${entry.issues} issues) [${entry.checked}/${entry.total}]`;
        case 'file_checked': return `File: ${entry.name} (${entry.issues} issues)`;
        case 'complete': return `Complete! Score: ${entry.score?.toFixed(1)}% — ${entry.total_issues} issues found`;
        case 'error': return `Error: ${entry.message}`;
        default: return JSON.stringify(entry);
      }
    },

    // ─── Reset ───────────────────────────────────────────────
    resetAll() {
      this.step = 2;
      this.selectedCourse = null;
      this.jobId = null;
      this.progressLog = [];
      this.progressPct = 0;
      this.currentPhaseLabel = '';
      this.result = null;
      this.fixResult = null;
      this.selectedFixes = [];
      this.courseMeta = null;
      this.aiSuggestions = {};
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }
    },
  };
}
