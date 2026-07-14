/* =========================================================================
   health.js
   -------------------------------------------------------------------------
   Module 1: Employee Health Data Management.
   Mirrors the apiRequest() pattern in auth.js, but these endpoints are
   JWT-protected, so every call attaches an Authorization header.
   ========================================================================= */

async function healthApiRequest(path, { method = "GET", body, token } = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      // Validation errors come back as { message, errors: [...] } — surface
      // the specific field problems rather than a generic message.
      const detail = Array.isArray(data.errors) && data.errors.length
        ? `${data.message}: ${data.errors.join("; ")}`
        : data.message || `Request failed (status ${response.status})`;
      throw new Error(detail);
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("Couldn't reach the server. Is the backend running?");
    }
    throw error;
  }
}

function createHealthRecord(payload, token) {
  return healthApiRequest("/health-records", { method: "POST", body: payload, token });
}

function listHealthRecords(token) {
  return healthApiRequest("/health-records", { method: "GET", token });
}

function getHealthRecord(id, token) {
  return healthApiRequest(`/health-records/${id}`, { method: "GET", token });
}

function updateHealthRecord(id, payload, token) {
  return healthApiRequest(`/health-records/${id}`, { method: "PUT", body: payload, token });
}

function deleteHealthRecord(id, token) {
  return healthApiRequest(`/health-records/${id}`, { method: "DELETE", token });
}
