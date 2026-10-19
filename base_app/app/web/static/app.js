// Shared helpers used by both login.html and admin.html.
// Tokens are the two "wristbands" from PROJECT_GUIDE.md: a short-lived
// access token and a longer-lived refresh token, kept in localStorage so
// a page reload doesn't log you out.

const API_BASE = "/api/v1";

function getAccessToken() {
  return localStorage.getItem("sellphi_access_token");
}

function getRefreshToken() {
  return localStorage.getItem("sellphi_refresh_token");
}

function setTokens(accessToken, refreshToken) {
  localStorage.setItem("sellphi_access_token", accessToken);
  localStorage.setItem("sellphi_refresh_token", refreshToken);
}

function clearTokens() {
  localStorage.removeItem("sellphi_access_token");
  localStorage.removeItem("sellphi_refresh_token");
}

function goToLogin() {
  window.location.href = "/login";
}

async function tryRefresh() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;

  const data = await response.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

// Fetch wrapper that attaches the access token and, if the server says it's
// expired, quietly trades the refresh token for a new one and retries once
// before giving up and sending the person back to the login page.
async function apiFetch(path, options = {}) {
  const doFetch = () => {
    const headers = new Headers(options.headers || {});
    const accessToken = getAccessToken();
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    return fetch(`${API_BASE}${path}`, { ...options, headers });
  };

  let response = await doFetch();
  if (response.status === 401 && getRefreshToken()) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      response = await doFetch();
    }
  }
  return response;
}

async function requireLogin() {
  if (!getAccessToken()) {
    goToLogin();
    return null;
  }
  const response = await apiFetch("/auth/me");
  if (!response.ok) {
    clearTokens();
    goToLogin();
    return null;
  }
  return response.json();
}
