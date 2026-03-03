/**
 * A11yScope — Admin panel Alpine.js component
 */
function adminApp() {
  return {
    tab: 'users',
    users: [],
    auditLogs: [],
    settings: [],
    loading: false,
    error: '',

    // User form
    showUserForm: false,
    userForm: { email: '', display_name: '', role: 'auditor', password: '' },

    // Audit log filters
    auditFilter: { action: '', limit: 50 },
    auditTotal: 0,

    // Setting form
    settingForm: { key: '', value: '' },

    async init() {
      await this.loadUsers();
    },

    // ─── Users ─────────────────────────────────────────
    async loadUsers() {
      this.loading = true;
      try {
        const resp = await fetchWithAuth('/api/admin/users');
        if (resp.ok) this.users = await resp.json();
      } catch (e) {
        this.error = 'Failed to load users';
      } finally {
        this.loading = false;
      }
    },

    async createUser() {
      try {
        const resp = await fetchWithAuth('/api/admin/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.userForm),
        });
        if (resp.ok) {
          this.showUserForm = false;
          this.userForm = { email: '', display_name: '', role: 'auditor', password: '' };
          await this.loadUsers();
        } else {
          const data = await resp.json();
          alert(data.detail || 'Failed to create user');
        }
      } catch (e) {
        alert('Error: ' + e.message);
      }
    },

    async toggleUserActive(userId, isActive) {
      await fetchWithAuth(`/api/admin/users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !isActive }),
      });
      await this.loadUsers();
    },

    async changeUserRole(userId, newRole) {
      await fetchWithAuth(`/api/admin/users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole }),
      });
      await this.loadUsers();
    },

    async deleteUser(userId) {
      if (!confirm('Deactivate this user?')) return;
      await fetchWithAuth(`/api/admin/users/${userId}`, { method: 'DELETE' });
      await this.loadUsers();
    },

    // ─── Audit Logs ────────────────────────────────────
    async loadAuditLogs() {
      this.loading = true;
      try {
        const params = new URLSearchParams();
        if (this.auditFilter.action) params.set('action', this.auditFilter.action);
        params.set('limit', this.auditFilter.limit);

        const resp = await fetchWithAuth(`/api/admin/audit-logs?${params}`);
        if (resp.ok) {
          const data = await resp.json();
          this.auditLogs = data.entries || [];
          this.auditTotal = data.total || 0;
        }
      } catch (e) {
        this.error = 'Failed to load audit logs';
      } finally {
        this.loading = false;
      }
    },

    // ─── Settings ──────────────────────────────────────
    async loadSettings() {
      this.loading = true;
      try {
        const resp = await fetchWithAuth('/api/admin/settings');
        if (resp.ok) this.settings = await resp.json();
      } catch (e) {
        this.error = 'Failed to load settings';
      } finally {
        this.loading = false;
      }
    },

    async saveSetting() {
      if (!this.settingForm.key) return;
      await fetchWithAuth('/api/admin/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.settingForm),
      });
      this.settingForm = { key: '', value: '' };
      await this.loadSettings();
    },

    formatDate(d) {
      if (!d) return '—';
      return new Date(d).toLocaleString();
    },
  };
}
