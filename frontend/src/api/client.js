/**
 * API client — fetch wrappers for all Orion dashboard endpoints.
 */

const BASE = '/api/v1/dashboard';

let authToken = null;
let currentWorkspaceId = null;

export function setAuthToken(token) {
  authToken = token;
}

export function setWorkspaceId(id) {
  currentWorkspaceId = id;
}

async function request(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  if (currentWorkspaceId) {
    headers['X-Workspace-ID'] = currentWorkspaceId;
  }
  
  const res = await fetch(url, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Fetch paginated RTM matrix rows. */
export async function fetchMatrix({ page = 1, pageSize = 50, status, sort, order, search } = {}) {
  const params = new URLSearchParams();
  params.set('page', page);
  params.set('page_size', pageSize);
  if (status) params.set('status', status);
  if (sort) params.set('sort', sort);
  if (order) params.set('order', order);
  if (search) params.set('search', search);
  return request(`${BASE}/matrix?${params}`);
}

/** Reclassify with custom thresholds (live preview, no persist). */
export async function reclassifyMatrix(coveredThreshold, driftedThreshold) {
  return request(`${BASE}/matrix/reclassify`, {
    method: 'POST',
    body: JSON.stringify({
      covered_threshold: coveredThreshold,
      drifted_threshold: driftedThreshold,
    }),
  });
}

/** Fetch XAI heatmap data for a specific traceability entry. */
export async function fetchHeatmap(entryId) {
  return request(`${BASE}/matrix/${entryId}/heatmap`);
}

/** Fetch summary statistics. */
export async function fetchStats() {
  return request(`${BASE}/stats`);
}

/** Run simulate-webhook demo. */
export async function simulateWebhook(payload) {
  return request(`${BASE}/simulate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/** Override a risk score manually (Requires QA_LEAD). */
export async function overrideRiskScore(entryId, newStatus, rationale) {
  return request(`${BASE}/matrix/${entryId}/override`, {
    method: 'POST',
    body: JSON.stringify({
      new_status: newStatus,
      rationale: rationale,
    }),
  });
}
/** Fetch user workspaces. */
export async function fetchWorkspaces() {
  // Not using BASE here since it's /api/v1/auth
  return request('/api/v1/auth/workspaces');
}

/** Fetch background tasks. */
export async function fetchTasks(limit = 10) {
  return request(`/api/v1/tasks?limit=${limit}`);
}

/** Fetch all workspace integrations status (Jira, GitHub, Ollama). */
export async function fetchIntegrationsStatus() {
  return request('/api/v1/integrations/status');
}

/** Test Jira connection with current or custom credentials. */
export async function testJiraConnection(payload = {}) {
  return request('/api/v1/integrations/jira/test', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/** Test GitHub App PEM key & JWT minting. */
export async function testGitHubConnection() {
  return request('/api/v1/integrations/github/test', {
    method: 'POST',
  });
}

/** Trigger on-demand Jira sync for the workspace. */
export async function syncJira(projectKey = null) {
  const url = projectKey ? `/api/v1/jira/sync?project_key=${encodeURIComponent(projectKey)}` : '/api/v1/jira/sync';
  return request(url, {
    method: 'POST',
  });
}
