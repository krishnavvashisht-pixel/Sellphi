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
  const token = getAccessToken();
  if (!token) {
    return null;
  }
  const response = await apiFetch("/auth/me");
  if (!response.ok) {
    return null;
  }
  return response.json();
}

/* ==========================================================================
   Milestone 2: Deliverability AI Scorer (Lavender-style analyzer)
   ========================================================================== */
const SPAM_KEYWORDS = [
  "guarantee", "guaranteed", "100%", "free", "risk-free", "risk free",
  "revolutionary", "miracle", "act now", "urgent", "no obligation",
  "earn money", "winner", "congratulations", "click here", "unbelievable"
];

function analyzeEmailDeliverability(subject = "", body = "") {
  const fullText = `${subject} ${body}`.toLowerCase();
  const words = fullText.trim().split(/\s+/).filter(Boolean);
  const wordCount = words.length;
  const readingTimeSec = Math.max(1, Math.round(wordCount / 3.2)); // ~190 words/min = 3.2 words/sec

  // Spam keyword search
  const spamWordsFound = [];
  for (const kw of SPAM_KEYWORDS) {
    if (fullText.includes(kw) && !spamWordsFound.includes(kw)) {
      spamWordsFound.push(kw);
    }
  }

  // Count question marks (CTAs)
  const questionsCount = (fullText.match(/\?/g) || []).length;

  // Calculate Lavender score (0 - 100)
  let score = 96;

  // Word count penalties
  if (wordCount < 30) score -= 12; // Too brief / lacking substance
  else if (wordCount > 130) score -= 15; // Too long for cold email
  else if (wordCount > 180) score -= 25; // High bounce risk

  // Question count penalties (optimal is 1 soft ask)
  if (questionsCount === 0) score -= 10;
  else if (questionsCount > 2) score -= 15;

  // Spam word penalties
  score -= (spamWordsFound.length * 15);

  score = Math.max(25, Math.min(98, score));

  let grade = "excellent";
  let gradeText = "Great Deliverability";
  if (score < 65) {
    grade = "poor";
    gradeText = "High Spam Risk";
  } else if (score < 80) {
    grade = "good";
    gradeText = "Good (Needs Polish)";
  }

  return {
    score,
    grade,
    gradeText,
    wordCount,
    readingTimeSec,
    questionsCount,
    spamWordsFound,
  };
}

/* ==========================================================================
   Milestone 1: Command Palette (Cmd + K / Ctrl + K)
   ========================================================================== */
function setupCommandPalette() {
  if (document.getElementById("cmd-palette-modal")) return;

  const modalHtml = `
    <div id="cmd-palette-modal" class="cmd-palette-backdrop hidden">
      <div class="cmd-palette-box" role="dialog" aria-modal="true">
        <div class="cmd-input-wrap">
          <span style="font-size:18px;">⚡</span>
          <input id="cmd-search-input" type="text" placeholder="Type a command or search... (Esc to close)" autocomplete="off" />
          <span class="cmd-shortcut-badge">ESC</span>
        </div>
        <div class="cmd-list" id="cmd-items-list">
          <!-- Populated by JS -->
        </div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML("beforeend", modalHtml);

  const modal = document.getElementById("cmd-palette-modal");
  const input = document.getElementById("cmd-search-input");
  const list = document.getElementById("cmd-items-list");

  const defaultCommands = [
    { id: "scan", group: "Outbound Radar", title: "Scan Market Radar", desc: "Trigger Gemini live buying signal radar", icon: "📡", action: () => {
      const scanInput = document.getElementById("query-input") || document.getElementById("radar-query");
      if (scanInput) { scanInput.focus(); scanInput.scrollIntoView({ behavior: "smooth" }); }
      else window.location.href = "/dashboard";
    }},
    { id: "pipeline", group: "Outbound Radar", title: "Open Pipeline CRM", desc: "View and manage active saved opportunities", icon: "💼", action: () => {
      const openPipeBtn = document.getElementById("open-pipeline-btn");
      if (openPipeBtn) openPipeBtn.click();
      else window.location.href = "/dashboard";
    }},
    { id: "product", group: "Outbound Radar", title: "Add Product Offering", desc: "Configure high-value product to pitch", icon: "➕", action: () => {
      if (typeof openAddProductModal === "function") openAddProductModal();
      else window.location.href = "/dashboard";
    }},
    { id: "admin", group: "Administration & Security", title: "Admin Console", desc: "RBAC roles, user management & invitations", icon: "👑", action: () => {
      window.location.href = "/admin";
    }},
    { id: "mfa", group: "Administration & Security", title: "Two-Factor Authentication (MFA)", desc: "Open 2FA security credentials modal", icon: "🛡️", action: () => {
      const mfaBtn = document.getElementById("btn-mfa-modal");
      if (mfaBtn) mfaBtn.click();
      else window.location.href = "/admin";
    }},
    { id: "csv", group: "Actions", title: "Export Pipeline to CSV", desc: "Download qualified leads in CRM format", icon: "📥", action: () => {
      if (typeof exportPipelineCsv === "function") exportPipelineCsv();
      else alert("Open Dashboard to export pipeline.");
    }},
    { id: "logout", group: "Session", title: "Log Out", desc: "Clear session tokens and exit", icon: "🚪", action: () => {
      clearTokens();
      goToLogin();
    }}
  ];

  function renderCommands(items) {
    if (!items.length) {
      list.innerHTML = `<div style="text-align:center; padding:28px; color:var(--muted); font-size:13px;">No matching commands found.</div>`;
      return;
    }
    let html = "";
    let currentGroup = "";
    items.forEach((cmd, idx) => {
      if (cmd.group !== currentGroup) {
        currentGroup = cmd.group;
        html += `<div class="cmd-group-title">${currentGroup}</div>`;
      }
      html += `
        <div class="cmd-item ${idx === 0 ? 'selected' : ''}" data-cmd-id="${cmd.id}">
          <div class="cmd-item-left">
            <span style="font-size:17px;">${cmd.icon}</span>
            <div>
              <div style="font-weight:600;">${cmd.title}</div>
              <div style="font-size:11.5px; color:var(--muted);">${cmd.desc}</div>
            </div>
          </div>
          <span class="cmd-shortcut-badge">↵ Enter</span>
        </div>
      `;
    });
    list.innerHTML = html;
  }

  function openPalette() {
    modal.classList.remove("hidden");
    input.value = "";
    renderCommands(defaultCommands);
    setTimeout(() => input.focus(), 50);
  }

  function closePalette() {
    modal.classList.add("hidden");
  }

  // Keyboard listeners
  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (modal.classList.contains("hidden")) openPalette();
      else closePalette();
    } else if (e.key === "Escape" && !modal.classList.contains("hidden")) {
      closePalette();
    }
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closePalette();
  });

  input.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) { renderCommands(defaultCommands); return; }
    const filtered = defaultCommands.filter(c =>
      c.title.toLowerCase().includes(q) || c.desc.toLowerCase().includes(q) || c.group.toLowerCase().includes(q)
    );
    renderCommands(filtered);
  });

  list.addEventListener("click", (e) => {
    const item = e.target.closest(".cmd-item");
    if (!item) return;
    const cmdId = item.dataset.cmdId;
    const cmd = defaultCommands.find(c => c.id === cmdId);
    if (cmd) {
      closePalette();
      cmd.action();
    }
  });
}

// Auto-initialize Command Palette on load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setupCommandPalette);
} else {
  setupCommandPalette();
}
