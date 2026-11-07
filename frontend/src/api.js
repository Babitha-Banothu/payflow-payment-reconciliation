
const API_BASE_URL = "/api/v1";

async function request(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || `Request failed with status ${response.status}`
    );
  }

  return data;
}

// ==============================
// EXCEPTIONS API
// ==============================

export async function getAllExceptions({
  status = "",
  severity = "",
  issueType = "",
  limit = 100,
  offset = 0,
} = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  if (status) params.set("status", status);
  if (severity) params.set("severity", severity);
  if (issueType) params.set("issue_type", issueType);

  return request(`/exceptions?${params.toString()}`);
}

export async function getExceptionDetails(exceptionId) {
  return request(`/exceptions/${exceptionId}`);
}

export async function investigateException(exceptionId, payload) {
  return request(`/exceptions/${exceptionId}/investigate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resolveException(exceptionId, payload) {
  return request(`/exceptions/${exceptionId}/resolve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getExceptionHistory(exceptionId) {
  return request(`/exceptions/${exceptionId}/history`);
}

// ==============================
// TRANSACTIONS API
// ==============================

export async function getAllTransactions({
  search = "",
  status = "",
  currency = "",
  merchantId = "",
  dateFrom = "",
  dateTo = "",
  limit = 20,
  offset = 0,
} = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  if (search) params.set("search", search);
  if (status) params.set("status", status);
  if (currency) params.set("currency", currency);
  if (merchantId) params.set("merchant_id", merchantId);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);

  return request(`/transactions?${params.toString()}`);
}

export async function getTransactionDetails(paymentId) {
  return request(`/transactions/${encodeURIComponent(paymentId)}`);
}


// ==============================
// RECONCILIATION API
// ==============================

export async function getAllReconciliation({
  search = "",
  status = "",
  method = "",
  merchantId = "",
  limit = 20,
  offset = 0,
} = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  if (search) params.set("search", search);
  if (status) params.set("status", status);
  if (method) params.set("method", method);
  if (merchantId) params.set("merchant_id", merchantId);

  return request(`/reconciliation?${params.toString()}`);
}

export async function getReconciliationDetails(matchId) {
  return request(
    `/reconciliation/${encodeURIComponent(matchId)}`
  );
}


// ==============================
// AUDIT HISTORY API
// ==============================

export async function getAuditHistory({
  search = "",
  entityType = "",
  action = "",
  limit = 20,
  offset = 0,
} = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  if (search) params.set("search", search);
  if (entityType) params.set("entity_type", entityType);
  if (action) params.set("action", action);

  return request(`/audit?${params.toString()}`);
}
export async function getReportsOverview() {
  return request("/reports/overview");
}