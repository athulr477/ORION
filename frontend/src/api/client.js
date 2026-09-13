/**
 * API client — fetch wrappers for all Orion dashboard endpoints.
 */

const BASE = '/api/v1/dashboard';

async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
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
