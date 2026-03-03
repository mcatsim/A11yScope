/**
 * A11yScope — Alpine.js Dashboard App (v3.0 — dashboard shell)
 */

/**
 * Helper: fetch with Authorization header + auto-refresh
 */
async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  let resp = await fetch(url, { ...options, headers });

  // If 401, try to refresh
  if (resp.status === 401 && token) {
    const refreshResp = await fetch('/api/auth/refresh', { method: 'POST' });
    if (refreshResp.ok) {
      const data = await refreshResp.json();
      localStorage.setItem('access_token', data.access_token);
      headers['Authorization'] = `Bearer ${data.access_token}`;
      return fetch(url, { ...options, headers });
    } else {
      localStorage.removeItem('access_token');
    }
  }
  return resp;
}

function dashboardApp() {
  return {
    // ─── Auth state ────────────────────────────────────────
    authMode: 'none',
    authUser: null,
    showLogin: false,
    loginEmail: '',
    loginPassword: '',
    loginError: '',
    loginLoading: false,
    showChangePassword: false,
    cpCurrentPassword: '',
    cpNewPassword: '',
    cpError: '',

    // ─── Dashboard state ───────────────────────────────────
    currentView: 'dashboard',
    sidebarOpen: false,
    showNewScanModal: false,
    selectedScanId: null,

    // ─── Dashboard data ────────────────────────────────────
    activeScans: [],
    queuedScans: [],
    recentScans: [],
    dashboardWsMap: {},      // job_id -> WebSocket (per active scan)
    dashboardInterval: null, // polling interval handle

    // ─── API Keys ──────────────────────────────────────────
    savedKeys: [],
    showAddKeyForm: false,
    newKeyLabel: '',
    newKeyUrl: '',
    newKeyToken: '',
    keyError: '',

    // ─── Scan state (preserved for scan detail view) ───────
    result: null,
    jobId: null,
    progressLog: [],
    currentPhaseLabel: '',
    progressPct: 0,
    ws: null,

    // ─── Scan detail view state ──────────────────────────────
    detailScan: null,
    detailItems: [],
    detailStats: { items_done: 0, items_total: 0, issues: 0, files_done: 0, files_total: 0, progress_pct: 0 },
    detailWs: null,
    detailLoading: false,
    detailPhases: [
      { key: 'fetching', label: 'Fetching' },
      { key: 'checking', label: 'Checking' },
      { key: 'files', label: 'Files' },
      { key: 'scoring', label: 'Scoring' },
    ],
    detailCurrentPhase: null,
    detailPollTimer: null,

    // ─── Fix state (preserved for scan detail view) ────────
    selectedFixes: [],
    pushToCanvas: false,
    fixing: false,
    fixResult: null,

    // ─── AI config ─────────────────────────────────────────
    aiProvider: '',
    aiApiKey: '',
    aiModel: '',
    aiValidating: false,
    aiValidated: false,
    aiError: '',
    aiSuggestions: {},

    // ─── Init ──────────────────────────────────────────────
    async init() {
      // Check auth mode
      try {
        const resp = await fetch('/api/auth/sso/metadata');
        const data = await resp.json();
        this.authMode = data.auth_mode || 'none';
      } catch (e) {
        this.authMode = 'none';
      }

      // If auth_mode != none, check for existing token
      if (this.authMode !== 'none') {
        const token = localStorage.getItem('access_token');
        if (token) {
          try {
            const resp = await fetchWithAuth('/api/auth/me');
            if (resp.ok) {
              this.authUser = await resp.json();
              if (this.authUser.must_change_password || new URLSearchParams(location.search).get('change_password')) {
                this.showChangePassword = true;
                return;
              }
            } else {
              localStorage.removeItem('access_token');
              this.showLogin = true;
              return;
            }
          } catch (e) {
            localStorage.removeItem('access_token');
            this.showLogin = true;
            return;
          }
        } else {
          this.showLogin = true;
          return;
        }
      }

      // Auth is resolved — load dashboard data
      await this.loadDashboardData();
    },

    // ─── Dashboard data loading ────────────────────────────
    async loadDashboardData() {
      // Load keys, scans in parallel
      await Promise.allSettled([
        this.loadKeys(),
        this.loadScans(),
      ]);
      // Start dashboard polling if we're on the dashboard view
      if (this.currentView === 'dashboard') {
        this.startDashboardPolling();
      }
    },

    async loadKeys() {
      try {
        const resp = await fetchWithAuth('/api/keys');
        if (resp.ok) {
          this.savedKeys = await resp.json();
        }
      } catch (e) {
        // Keys endpoint may not exist yet — ignore
      }
    },

    async loadScans() {
      try {
        const resp = await fetchWithAuth('/api/scans');
        if (resp.ok) {
          const scans = await resp.json();
          this.activeScans = scans.filter(s => s.status === 'running');
          this.queuedScans = scans.filter(s => s.status === 'queued' || s.status === 'pending');
          this.recentScans = scans.filter(s => s.status === 'complete' || s.status === 'failed')
            .sort((a, b) => new Date(b.completed_at || b.created_at) - new Date(a.completed_at || a.created_at))
            .slice(0, 20);
          // Manage per-scan WebSocket connections for active scans on dashboard
          if (this.currentView === 'dashboard') {
            this.syncDashboardWs();
          }
        }
      } catch (e) {
        // Scans endpoint may not exist yet — ignore
      }
    },

    // ─── Navigation ────────────────────────────────────────
    navigateTo(view) {
      // Stop dashboard polling/ws when leaving dashboard
      if (this.currentView === 'dashboard' && view !== 'dashboard') {
        this.stopDashboardPolling();
        this.closeDashboardWs();
      }

      this.currentView = view;
      this.sidebarOpen = false; // close mobile sidebar on nav

      // Clean up detail view ws/polling when leaving detail
      if (this.currentView === 'detail' && view !== 'detail') {
        this.closeDetailWs();
      }

      // Refresh data when navigating to certain views
      if (view === 'dashboard') {
        this.loadScans();
        this.startDashboardPolling();
      } else if (view === 'keys') {
        this.loadKeys();
      } else if (view === 'history') {
        this.loadScans();
      } else if (view === 'detail') {
        this.loadScanDetail(this.selectedScanId);
      }
    },

    get viewTitle() {
      const titles = {
        dashboard: 'Dashboard',
        keys: 'API Keys',
        history: 'Scan History',
        detail: 'Scan Detail',
        admin: 'Administration',
      };
      return titles[this.currentView] || 'Dashboard';
    },

    // ─── Auth ──────────────────────────────────────────────
    async login() {
      this.loginLoading = true;
      this.loginError = '';
      try {
        const resp = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: this.loginEmail, password: this.loginPassword }),
        });
        const data = await resp.json();
        if (resp.ok) {
          localStorage.setItem('access_token', data.access_token);
          if (data.must_change_password) {
            this.showLogin = false;
            this.showChangePassword = true;
            const meResp = await fetchWithAuth('/api/auth/me');
            if (meResp.ok) this.authUser = await meResp.json();
          } else {
            this.showLogin = false;
            const meResp = await fetchWithAuth('/api/auth/me');
            if (meResp.ok) this.authUser = await meResp.json();
            // Load dashboard data after login
            await this.loadDashboardData();
          }
        } else {
          this.loginError = data.detail || 'Login failed';
        }
      } catch (e) {
        this.loginError = 'Network error: ' + e.message;
      } finally {
        this.loginLoading = false;
      }
    },

    async changePassword() {
      this.cpError = '';
      try {
        const resp = await fetchWithAuth('/api/auth/change-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            current_password: this.cpCurrentPassword,
            new_password: this.cpNewPassword,
          }),
        });
        if (resp.ok) {
          this.showChangePassword = false;
          // Re-login with new password
          const loginResp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: this.authUser.email, password: this.cpNewPassword }),
          });
          if (loginResp.ok) {
            const data = await loginResp.json();
            localStorage.setItem('access_token', data.access_token);
            const meResp = await fetchWithAuth('/api/auth/me');
            if (meResp.ok) this.authUser = await meResp.json();
          }
          // Load dashboard data after password change
          await this.loadDashboardData();
        } else {
          const data = await resp.json();
          this.cpError = data.detail || 'Failed to change password';
        }
      } catch (e) {
        this.cpError = 'Error: ' + e.message;
      }
    },

    async logout() {
      this.stopDashboardPolling();
      this.closeDashboardWs();
      this.closeDetailWs();
      try {
        await fetchWithAuth('/api/auth/logout', { method: 'POST' });
      } catch (e) {}
      localStorage.removeItem('access_token');
      this.authUser = null;
      this.showLogin = true;
      this.currentView = 'dashboard';
      this.activeScans = [];
      this.queuedScans = [];
      this.recentScans = [];
      this.savedKeys = [];
    },

    get isAdmin() {
      return this.authMode === 'none' || (this.authUser && this.authUser.role === 'admin');
    },

    get canAudit() {
      return this.authMode === 'none' || (this.authUser && ['admin', 'auditor'].includes(this.authUser.role));
    },

    // ─── Dashboard computed ─────────────────────────────────
    get dashboardRecent() {
      return this.recentScans.slice(0, 10);
    },

    get displayName() {
      if (this.authUser) return this.authUser.display_name || this.authUser.email;
      return '';
    },

    ssoLogin() {
      window.location.href = '/api/auth/sso/' + (this.authMode === 'sso' ? 'oidc' : 'oidc') + '/login';
    },

    // ─── API Key Management ────────────────────────────────
    async addKey() {
      this.keyError = '';
      try {
        const resp = await fetchWithAuth('/api/keys', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            label: this.newKeyLabel,
            canvas_base_url: this.newKeyUrl,
            canvas_api_token: this.newKeyToken,
          }),
        });
        if (resp.ok) {
          this.showAddKeyForm = false;
          this.newKeyLabel = '';
          this.newKeyUrl = '';
          this.newKeyToken = '';
          await this.loadKeys();
        } else {
          const data = await resp.json();
          this.keyError = data.detail || 'Failed to save key';
        }
      } catch (e) {
        this.keyError = 'Network error: ' + e.message;
      }
    },

    async deleteKey(keyId) {
      if (!confirm('Delete this API key? This cannot be undone.')) return;
      try {
        await fetchWithAuth(`/api/keys/${keyId}`, { method: 'DELETE' });
        await this.loadKeys();
      } catch (e) {
        // ignore
      }
    },

    // ─── Dashboard polling & WebSocket ─────────────────────
    startDashboardPolling() {
      this.stopDashboardPolling(); // clear any existing interval
      this.dashboardInterval = setInterval(() => {
        this.loadScans();
      }, 3000);
    },

    stopDashboardPolling() {
      if (this.dashboardInterval) {
        clearInterval(this.dashboardInterval);
        this.dashboardInterval = null;
      }
    },

    syncDashboardWs() {
      const activeIds = new Set(this.activeScans.map(s => s.job_id || s.id));

      // Close WS for scans that are no longer active
      for (const jobId of Object.keys(this.dashboardWsMap)) {
        if (!activeIds.has(jobId)) {
          try { this.dashboardWsMap[jobId].close(); } catch (e) {}
          delete this.dashboardWsMap[jobId];
        }
      }

      // Open WS for new active scans
      for (const scan of this.activeScans) {
        const jobId = scan.job_id || scan.id;
        if (!this.dashboardWsMap[jobId]) {
          this.openDashboardWs(jobId);
        }
      }
    },

    openDashboardWs(jobId) {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      let wsUrl = `${proto}://${location.host}/ws/scan/${jobId}`;
      const token = localStorage.getItem('access_token');
      if (token) {
        wsUrl += `?token=${encodeURIComponent(token)}`;
      }

      try {
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          // Update the matching active scan in-place
          const scan = this.activeScans.find(s => (s.job_id || s.id) === jobId);
          if (!scan) return;

          switch (msg.type) {
            case 'phase':
              scan.phase = msg.label || msg.phase;
              const phases = { fetching: 10, checking: 40, files: 70, scoring: 90 };
              if (phases[msg.phase]) scan.progress_pct = phases[msg.phase];
              break;
            case 'item_checked':
              scan.current_item = msg.title;
              scan.total_issues = (scan.total_issues || 0) + (msg.issues || 0);
              if (msg.total > 0) scan.progress_pct = 40 + (msg.checked / msg.total) * 30;
              break;
            case 'file_checked':
              scan.current_item = msg.name;
              break;
            case 'complete':
              scan.progress_pct = 100;
              scan.phase = 'complete';
              // Refresh scan lists to move this scan from active to recent
              this.loadScans();
              break;
            case 'error':
              scan.phase = 'error';
              this.loadScans();
              break;
          }
        };

        ws.onclose = () => {
          delete this.dashboardWsMap[jobId];
        };

        ws.onerror = () => {
          // Will fall back to polling
          try { ws.close(); } catch (e) {}
          delete this.dashboardWsMap[jobId];
        };

        this.dashboardWsMap[jobId] = ws;
      } catch (e) {
        // WebSocket not available — polling will handle it
      }
    },

    closeDashboardWs() {
      for (const jobId of Object.keys(this.dashboardWsMap)) {
        try { this.dashboardWsMap[jobId].close(); } catch (e) {}
      }
      this.dashboardWsMap = {};
    },

    // ─── Cancel scan ─────────────────────────────────────────
    async cancelScan(scanId) {
      try {
        await fetchWithAuth(`/api/scans/${scanId}`, { method: 'DELETE' });
        await this.loadScans();
      } catch (e) {
        // ignore — will refresh on next poll
      }
    },

    // ─── Scan Detail View ──────────────────────────────────
    async loadScanDetail(scanId) {
      if (!scanId) return;
      this.detailLoading = true;
      this.detailItems = [];
      this.detailStats = { items_done: 0, items_total: 0, issues: 0, files_done: 0, files_total: 0, progress_pct: 0 };
      this.detailCurrentPhase = null;
      this.result = null;

      try {
        const resp = await fetchWithAuth(`/api/scans/${scanId}`);
        if (!resp.ok) {
          this.detailScan = { status: 'failed', error: 'Failed to load scan (HTTP ' + resp.status + ')' };
          this.detailLoading = false;
          return;
        }
        const data = await resp.json();
        this.detailScan = data;
        this.jobId = scanId;

        if (data.status === 'complete' && data.result_json) {
          // Completed scan — show results
          this.result = data.result_json;
          this.detailCurrentPhase = 'complete';
          this.detailStats.progress_pct = 100;
        } else if (data.status === 'complete' && data.result) {
          this.result = data.result;
          this.detailCurrentPhase = 'complete';
          this.detailStats.progress_pct = 100;
        } else if (data.status === 'failed') {
          this.detailCurrentPhase = 'error';
        } else if (data.status === 'running') {
          // Running scan — connect WebSocket for live updates
          this.detailCurrentPhase = data.current_phase || data.phase || 'fetching';
          if (data.progress_pct) this.detailStats.progress_pct = data.progress_pct;
          this.openDetailWs(scanId);
        } else {
          // Queued or pending — start polling
          this.startDetailPolling(scanId);
        }
      } catch (e) {
        this.detailScan = { status: 'failed', error: 'Network error: ' + e.message };
      } finally {
        this.detailLoading = false;
      }
    },

    openDetailWs(scanId) {
      this.closeDetailWs(); // clean up any prior connection

      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      let wsUrl = `${proto}://${location.host}/ws/scan/${scanId}`;
      const token = localStorage.getItem('access_token');
      if (token) {
        wsUrl += `?token=${encodeURIComponent(token)}`;
      }

      try {
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          this.handleDetailMessage(msg);
        };

        ws.onclose = () => {
          this.detailWs = null;
          // If the scan is still running, fall back to polling
          if (this.detailScan && this.detailScan.status === 'running' && this.currentView === 'detail') {
            this.startDetailPolling(scanId);
          }
        };

        ws.onerror = () => {
          try { ws.close(); } catch (e) {}
          this.detailWs = null;
          // Fall back to polling
          if (this.currentView === 'detail') {
            this.startDetailPolling(scanId);
          }
        };

        this.detailWs = ws;
      } catch (e) {
        // WebSocket not available — polling will handle it
        this.startDetailPolling(scanId);
      }
    },

    handleDetailMessage(msg) {
      const phaseOrder = ['fetching', 'checking', 'files', 'scoring'];

      switch (msg.type) {
        case 'phase':
          this.detailCurrentPhase = msg.phase || msg.label;
          const phases = { fetching: 10, checking: 40, files: 70, scoring: 90 };
          if (phases[msg.phase]) {
            this.detailStats.progress_pct = phases[msg.phase];
          }
          break;

        case 'item_start':
          // Mark previous active items as pending (in case we missed item_done)
          // Then add or mark this item as active
          {
            const existing = this.detailItems.find(i => i.title === msg.title);
            if (existing) {
              existing.status = 'active';
            } else {
              this.detailItems.push({
                id: msg.id || msg.title,
                title: msg.title || msg.name || 'Item',
                status: 'active',
                issues: null,
              });
            }
            // Mark all other items as no longer active (only one active at a time)
            this.detailItems.forEach(i => {
              if (i.title !== msg.title && i.status === 'active') {
                // Leave them as active — the item_done will handle transition
              }
            });
            this.scrollFeedToActive();
          }
          break;

        case 'item_found':
          // An item discovered during fetching phase
          {
            const exists = this.detailItems.find(i => i.title === (msg.title || msg.label));
            if (!exists) {
              this.detailItems.push({
                id: msg.id || msg.title || msg.label,
                title: msg.title || msg.label || 'Item',
                status: 'pending',
                issues: null,
              });
            }
            this.detailStats.items_total = msg.total || this.detailItems.length;
          }
          break;

        case 'item_done':
        case 'item_checked':
          {
            const item = this.detailItems.find(i => i.title === msg.title);
            if (item) {
              item.status = 'done';
              item.issues = msg.issues || 0;
            } else {
              this.detailItems.push({
                id: msg.id || msg.title,
                title: msg.title || 'Item',
                status: 'done',
                issues: msg.issues || 0,
              });
            }
            this.detailStats.items_done = msg.checked || (this.detailItems.filter(i => i.status === 'done').length);
            this.detailStats.items_total = msg.total || this.detailStats.items_total || this.detailItems.length;
            this.detailStats.issues = (this.detailStats.issues || 0) + (msg.issues || 0);
            if (msg.total > 0) {
              this.detailStats.progress_pct = 40 + (msg.checked / msg.total) * 30;
            }
          }
          break;

        case 'file_start':
          {
            const exists = this.detailItems.find(i => i.title === msg.name);
            if (exists) {
              exists.status = 'active';
            } else {
              this.detailItems.push({
                id: msg.id || msg.name,
                title: msg.name || 'File',
                status: 'active',
                issues: null,
              });
            }
            this.scrollFeedToActive();
          }
          break;

        case 'file_checked':
        case 'file_done':
          {
            const item = this.detailItems.find(i => i.title === msg.name);
            if (item) {
              item.status = 'done';
              item.issues = msg.issues || 0;
            } else {
              this.detailItems.push({
                id: msg.id || msg.name,
                title: msg.name || 'File',
                status: 'done',
                issues: msg.issues || 0,
              });
            }
            this.detailStats.files_done = (this.detailStats.files_done || 0) + 1;
            this.detailStats.files_total = msg.total || this.detailStats.files_total || this.detailStats.files_done;
          }
          break;

        case 'stats':
          // Direct stats update from server
          if (msg.items_done != null) this.detailStats.items_done = msg.items_done;
          if (msg.items_total != null) this.detailStats.items_total = msg.items_total;
          if (msg.issues != null) this.detailStats.issues = msg.issues;
          if (msg.files_done != null) this.detailStats.files_done = msg.files_done;
          if (msg.files_total != null) this.detailStats.files_total = msg.files_total;
          if (msg.progress_pct != null) this.detailStats.progress_pct = msg.progress_pct;
          break;

        case 'complete':
          this.detailCurrentPhase = 'complete';
          this.detailStats.progress_pct = 100;
          if (this.detailScan) this.detailScan.status = 'complete';
          // Load full results
          this.loadScanResult(this.selectedScanId);
          // Refresh dashboard data in the background
          this.loadScans();
          break;

        case 'error':
          this.detailCurrentPhase = 'error';
          if (this.detailScan) {
            this.detailScan.status = 'failed';
            this.detailScan.error = msg.message || 'Unknown error';
          }
          this.loadScans();
          break;
      }
    },

    scrollFeedToActive() {
      this.$nextTick(() => {
        const feed = this.$refs.liveFeed;
        if (!feed) return;
        const activeItems = feed.querySelectorAll('.feed-item.active');
        if (activeItems.length > 0) {
          activeItems[activeItems.length - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      });
    },

    async loadScanResult(scanId) {
      try {
        const resp = await fetchWithAuth(`/api/scans/${scanId}`);
        if (resp.ok) {
          const data = await resp.json();
          this.detailScan = data;
          this.result = data.result_json || data.result || null;
        }
      } catch (e) {
        // Will retry on next poll
      }
    },

    startDetailPolling(scanId) {
      this.stopDetailPolling();
      this.detailPollTimer = setInterval(async () => {
        if (this.currentView !== 'detail') {
          this.stopDetailPolling();
          return;
        }
        try {
          const resp = await fetchWithAuth(`/api/scans/${scanId}`);
          if (resp.ok) {
            const data = await resp.json();
            this.detailScan = data;
            if (data.status === 'running' && !this.detailWs) {
              // Scan started running — try WebSocket again
              this.stopDetailPolling();
              this.detailCurrentPhase = data.current_phase || data.phase || 'fetching';
              this.openDetailWs(scanId);
            } else if (data.status === 'complete') {
              this.stopDetailPolling();
              this.detailCurrentPhase = 'complete';
              this.detailStats.progress_pct = 100;
              this.result = data.result_json || data.result || null;
              this.loadScans();
            } else if (data.status === 'failed') {
              this.stopDetailPolling();
              this.detailCurrentPhase = 'error';
            }
          }
        } catch (e) {
          // Keep polling
        }
      }, 2000);
    },

    stopDetailPolling() {
      if (this.detailPollTimer) {
        clearInterval(this.detailPollTimer);
        this.detailPollTimer = null;
      }
    },

    closeDetailWs() {
      this.stopDetailPolling();
      if (this.detailWs) {
        try { this.detailWs.close(); } catch (e) {}
        this.detailWs = null;
      }
    },

    closeDetailView() {
      this.closeDetailWs();
      this.detailScan = null;
      this.detailItems = [];
      this.detailStats = { items_done: 0, items_total: 0, issues: 0, files_done: 0, files_total: 0, progress_pct: 0 };
      this.detailCurrentPhase = null;
      this.result = null;
      this.selectedScanId = null;
      this.navigateTo('dashboard');
    },

    detailPhaseState(phaseKey) {
      const order = ['fetching', 'checking', 'files', 'scoring'];
      const currentIdx = order.indexOf(this.detailCurrentPhase);
      const phaseIdx = order.indexOf(phaseKey);

      if (this.detailCurrentPhase === 'complete') return 'done';
      if (this.detailCurrentPhase === 'error') {
        if (phaseIdx < currentIdx || currentIdx === -1) return 'done';
        if (phaseIdx === currentIdx) return 'error';
        return 'pending';
      }
      if (currentIdx === -1) return 'pending';
      if (phaseIdx < currentIdx) return 'done';
      if (phaseIdx === currentIdx) return 'active';
      return 'pending';
    },

    async cancelDetailScan() {
      if (!this.selectedScanId) return;
      if (!confirm('Cancel this scan? This cannot be undone.')) return;
      try {
        await fetchWithAuth(`/api/scans/${this.selectedScanId}`, { method: 'DELETE' });
        this.closeDetailView();
      } catch (e) {
        // ignore
      }
    },

    downloadReport() {
      if (!this.result) return;
      const report = {
        scan_id: this.selectedScanId,
        course_name: this.detailScan?.course_name || 'Unknown',
        overall_score: this.result.overall_score,
        total_issues: this.allIssues().length,
        content_items: this.result.content_items || [],
        file_items: this.result.file_items || [],
        issues: this.allIssues(),
        generated_at: new Date().toISOString(),
      };
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `a11yscope-report-${this.selectedScanId || 'scan'}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },

    // ─── Relative time formatting ────────────────────────────
    timeAgo(dateStr) {
      if (!dateStr) return '—';
      const now = Date.now();
      const then = new Date(dateStr).getTime();
      const diffSec = Math.floor((now - then) / 1000);

      if (diffSec < 10) return 'just now';
      if (diffSec < 60) return diffSec + 's ago';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return diffMin + 'm ago';
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return diffHr + 'h ago';
      const diffDay = Math.floor(diffHr / 24);
      if (diffDay < 7) return diffDay + 'd ago';
      if (diffDay < 30) return Math.floor(diffDay / 7) + 'w ago';
      return this.formatDate(dateStr);
    },

    // ─── Results helpers (preserved for scan detail view) ──
    scoreClass(score) {
      if (score == null) return '';
      if (score >= 90) return 'sc-pass';
      if (score >= 70) return 'sc-warn';
      return 'sc-fail';
    },

    getStandards(issue) {
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

    fixableIssues() {
      return this.allIssues().filter(i => i.auto_fixable && !i.fixed);
    },

    // ─── WebSocket & audit progress (preserved) ────────────
    connectWs() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      let wsUrl = `${proto}://${location.host}/ws/scan/${this.jobId}`;
      const token = localStorage.getItem('access_token');
      if (token) {
        wsUrl += `?token=${encodeURIComponent(token)}`;
      }
      this.ws = new WebSocket(wsUrl);

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        this.progressLog.push(msg);
        this.handleProgress(msg);
      };

      this.ws.onclose = () => {
        if (!this.result && this.jobId) {
          setTimeout(() => this.pollStatus(), 1000);
        }
      };

      this.ws.onerror = () => {
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
          this.loadScans();
          break;
        case 'error':
          this.currentPhaseLabel = 'Error: ' + msg.message;
          break;
      }
    },

    async pollStatus() {
      if (!this.jobId) return;
      try {
        const resp = await fetchWithAuth(`/api/scans/${this.jobId}`);
        const data = await resp.json();
        if (data.status === 'complete' && data.result) {
          this.result = data.result;
          this.progressPct = 100;
          this.loadScans();
        } else if (data.status === 'failed') {
          this.currentPhaseLabel = 'Failed: ' + (data.error || 'Unknown error');
        } else if (data.status === 'running') {
          setTimeout(() => this.pollStatus(), 2000);
        }
      } catch (e) {
        setTimeout(() => this.pollStatus(), 3000);
      }
    },

    // ─── Fix helpers (preserved) ───────────────────────────
    async applyFixes() {
      this.fixing = true;
      this.fixResult = null;
      try {
        const resp = await fetchWithAuth(`/api/fix/${this.jobId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            issue_indices: this.selectedFixes.map(Number),
            push_to_canvas: this.pushToCanvas,
          }),
        });
        this.fixResult = await resp.json();
      } catch (e) {
        this.fixResult = { fixed_count: 0, errors: ['Request failed: ' + e.message] };
      } finally {
        this.fixing = false;
      }
    },

    // ─── AI Suggestion (preserved) ─────────────────────────
    async getAISuggestion(issueIdx) {
      const issues = this.allIssues();
      if (issueIdx >= issues.length) return;
      issues[issueIdx]._aiLoading = true;
      try {
        const resp = await fetchWithAuth(`/api/ai/suggest/${this.jobId}`, {
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

    // ─── Log formatting ────────────────────────────────────
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

    // ─── Helpers ───────────────────────────────────────────
    formatDate(d) {
      if (!d) return '—';
      return new Date(d).toLocaleString();
    },
  };
}
