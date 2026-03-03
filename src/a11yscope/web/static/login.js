/**
 * A11yScope — Login page Alpine.js component
 */
function loginApp() {
  return {
    email: '',
    password: '',
    error: '',
    loading: false,
    authMode: 'none',
    ssoProtocol: null,

    async init() {
      // Check auth mode
      try {
        const resp = await fetch('/api/auth/sso/metadata');
        const data = await resp.json();
        this.authMode = data.auth_mode || 'none';
        this.ssoProtocol = data.sso_protocol;
      } catch (e) {
        // Default to none
      }

      // If already logged in, redirect
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const resp = await fetchWithAuth('/api/auth/me');
          if (resp.ok) {
            window.location.href = '/';
            return;
          }
        } catch (e) {
          localStorage.removeItem('access_token');
        }
      }

      // If auth_mode=none, go straight to app
      if (this.authMode === 'none') {
        window.location.href = '/';
      }
    },

    async login() {
      this.loading = true;
      this.error = '';
      try {
        const resp = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: this.email, password: this.password }),
        });
        const data = await resp.json();
        if (resp.ok) {
          localStorage.setItem('access_token', data.access_token);
          if (data.must_change_password) {
            window.location.href = '/?change_password=1';
          } else {
            window.location.href = '/';
          }
        } else {
          this.error = data.detail || 'Login failed';
        }
      } catch (e) {
        this.error = 'Network error: ' + e.message;
      } finally {
        this.loading = false;
      }
    },

    ssoLogin() {
      if (this.ssoProtocol === 'oidc') {
        window.location.href = '/api/auth/sso/oidc/login';
      } else if (this.ssoProtocol === 'saml') {
        window.location.href = '/api/auth/sso/saml/login';
      }
    },
  };
}

/**
 * Helper: fetch with Authorization header
 */
async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const resp = await fetch(url, { ...options, headers });

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
      window.location.href = '/login';
    }
  }
  return resp;
}
