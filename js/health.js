/* =========================================================================
   health.js
   -------------------------------------------------------------------------
   Module 1: Employee Health Data Management.
   Mirrors the apiRequest() pattern in auth.js, but these endpoints are
   JWT-protected, so every call attaches an Authorization header.
   ========================================================================= */

async function healthApiRequest(path, { method = "GET", body, token } = {}) {
  try {
    const isFormData = body instanceof FormData;
    const headers = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      cache: "no-store",
      body: isFormData ? body : (body ? JSON.stringify(body) : undefined),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 401 || response.status === 422) {
        if (typeof clearSession === "function") clearSession();
        window.location.href = "login-user.html";
        throw new Error("Session expired. Please sign in again.");
      }

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

const getHealthRecords = listHealthRecords;

function getHealthRecord(id, token) {
  return healthApiRequest(`/health-records/${id}`, { method: "GET", token });
}

function updateHealthRecord(id, payload, token) {
  return healthApiRequest(`/health-records/${id}`, { method: "PUT", body: payload, token });
}

function deleteHealthRecord(id, token) {
  return healthApiRequest(`/health-records/${id}`, { method: "DELETE", token });
}

function listReports(token) {
  return healthApiRequest("/reports", { method: "GET", token });
}

function uploadReport(formData, token) {
  return healthApiRequest("/reports/upload", { method: "POST", body: formData, token });
}

function deleteReport(id, token) {
  return healthApiRequest(`/reports/${id}`, { method: "DELETE", token });
}

/* A plain <a href="..."> can't view a report because the endpoint requires
   an Authorization header. Instead, fetch it as a blob with the token
   attached, then open that blob in a new tab. */
async function viewReport(id, token) {
  const response = await fetch(`${API_BASE_URL}/reports/${id}/file`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.message || `Couldn't open report (status ${response.status})`);
  }

  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  window.open(blobUrl, "_blank");
}

function getRiskPrediction(token) {
  return healthApiRequest("/risk", { method: "GET", token });
}

function getAdminDashboardStats(token) {
  return healthApiRequest("/admin/dashboard", { method: "GET", token });
}

function getAdminRecords(token) {
  return healthApiRequest("/admin/records", { method: "GET", token });
}

function deleteAdminRecord(id, token) {
  return healthApiRequest(`/admin/records/${id}`, { method: "DELETE", token });
}

function updateAdminRecordStatus(id, validationStatus, token) {
  return healthApiRequest(`/admin/records/${id}/status`, {
    method: "PUT",
    token,
    body: { validationStatus }
  });
}

function offboardAdminEmployee(userId, token) {
  return healthApiRequest(`/admin/employees/${userId}`, { method: "DELETE", token });
}

function offboardAdminEmployeeByEmail(email, token) {
  const encoded = encodeURIComponent(email.trim());
  return healthApiRequest(`/admin/employees/by-email/${encoded}`, { method: "DELETE", token });
}
