// All calls to the FastAPI backend live here.
// Endpoints are documented in the repository README ("Endpoints for Member 2").

const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const PAGE = 500; // backend maximum page size

// Turn any FastAPI error shape into one readable sentence.
function readError(data, status) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = (d.loc || []).filter((part) => part !== "body" && part !== "query").join(" ");
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  if (detail && Array.isArray(detail.errors)) {
    return detail.errors.map((e) => `Row ${e.row}: ${e.message}`).join("; ");
  }
  return `Request failed (${status}).`;
}

async function request(path, { method = "GET", body, query } = {}) {
  let url = BASE + path;
  if (query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") params.set(key, value);
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const options = { method };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.body = JSON.stringify(body);
    options.headers = { "Content-Type": "application/json" };
  }

  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("Cannot reach the server. Check that the backend is running.");
  }

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const error = new Error(readError(data, response.status));
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

// Lists are paginated on the server; fetch every page until a short page arrives.
// No artificial cap: lists are oldest-first, so a cap would drop the NEWEST entries.
async function fetchAll(path, query = {}) {
  const all = [];
  for (let offset = 0; ; offset += PAGE) {
    const page = await request(path, { query: { ...query, offset, limit: PAGE } });
    all.push(...page);
    if (page.length < PAGE) return all;
  }
}

export const api = {
  // Products and stock
  products: () => fetchAll("/api/products"),
  createProduct: (data, actor) => request("/api/products", { method: "POST", body: data, query: { actor } }),
  recordMovement: (data) => request("/api/stock-movements", { method: "POST", body: data }),
  movements: (productId) => fetchAll("/api/stock-movements", { product_id: productId }),
  alerts: () => fetchAll("/api/alerts"),
  importFile: (file, actor, dryRun) => {
    const form = new FormData();
    form.append("file", file);
    form.append("actor", actor);
    form.append("dry_run", String(dryRun));
    return request("/api/inventory/import", { method: "POST", body: form });
  },

  // Count + approval workflow
  submitCount: (data) => request("/api/workflow/stock-count", { method: "POST", body: data }),
  pending: () => fetchAll("/api/workflow/pending-approvals"),
  review: (requestId, data) =>
    request(`/api/workflow/approvals/${requestId}/review`, { method: "POST", body: data }),
  auditLogs: (filters = {}) => fetchAll("/api/workflow/audit-logs", filters),

  // Simulated Orbyte hub
  orbyteSync: (actor) => request("/api/integration/orbyte-sync", { method: "POST", body: { actor } }),
};
