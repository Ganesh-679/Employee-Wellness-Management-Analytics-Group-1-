/* =========================================================================
   auth.js
   -------------------------------------------------------------------------
   Every function here that starts with "call" sends a request to the
   backend. Right now there IS no backend yet — that's the next module of
   your internship project — so these functions are written and ready to
   go the moment your teammates stand up the API described in
   API_ENDPOINTS.md. Change API_BASE_URL below once you know your
   backend's real address.
   ========================================================================= */

// 👉 Change this one line once your backend is running.
const API_BASE_URL = "http://localhost:5000/api";

/* ---------- Toast notifications -----------------------------------------
   A "toast" is the small pop-up message in the corner of the screen (e.g.
   "Account created successfully"). Using toasts instead of alert() keeps
   the UI feeling modern and doesn't block the page. */
function showToast(message, type = "success") {
  let stack = document.querySelector(".toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "toast-stack";
    document.body.appendChild(stack);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", "status");
  toast.textContent = message;

  stack.appendChild(toast);

  // Auto-remove after 4 seconds so toasts don't pile up forever.
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

/** Shows a spinner inside a submit button and disables it while a request is in flight. */
function setButtonLoading(button, isLoading) {
  button.disabled = isLoading;
  button.classList.toggle("is-loading", isLoading);
}

/** Shows or hides the page-level alert banner (used for form-wide errors, e.g. "Invalid credentials"). */
function showAlertBanner(bannerEl, message, type = "error") {
  if (!bannerEl) return;
  bannerEl.textContent = message;
  bannerEl.classList.remove("alert-error", "alert-success");
  bannerEl.classList.add(type === "success" ? "alert-success" : "alert-error", "visible");
}

function hideAlertBanner(bannerEl) {
  if (!bannerEl) return;
  bannerEl.classList.remove("visible");
}

/* ---------- Generic request helper ---------------------------------------
   Wraps fetch() so every call handles JSON parsing and network failures
   the same way, instead of repeating try/catch everywhere. */
async function apiRequest(path, body) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    // The backend is expected to always return JSON, success or failure.
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      // e.g. { message: "Email already registered" }
      throw new Error(data.message || `Request failed (status ${response.status})`);
    }

    return data;
  } catch (error) {
    // Distinguish "server responded with an error" from "couldn't reach the server at all".
    if (error instanceof TypeError) {
      throw new Error("Couldn't reach the server. Is the backend running?");
    }
    throw error;
  }
}

/* ---------- One function per endpoint -------------------------------------
   Each of these maps 1:1 to a row in API_ENDPOINTS.md. Pages call these
   instead of calling fetch() directly. */

function registerUser({ email, password }) {
  return apiRequest("/user/register", { email, password });
}

function registerAdmin({ adminId, password }) {
  return apiRequest("/admin/register", { adminId, password });
}

function loginUser({ email, password, rememberMe }) {
  return apiRequest("/user/login", { email, password, rememberMe });
}

function loginAdmin({ adminId, password, rememberMe }) {
  return apiRequest("/admin/login", { adminId, password, rememberMe });
}

function requestPasswordReset({ identifier, role }) {
  // "identifier" is the user's email or the admin's ID — role tells the
  // backend which table to check.
  return apiRequest("/forgot-password", { identifier, role });
}

function resetPassword({ identifier, role, otp, newPassword }) {
  return apiRequest("/reset-password", { identifier, role, otp, newPassword });
}

/**
 * Small helper used on login pages: after a successful login, the backend
 * is expected to return a token. We stash it in-memory + sessionStorage so
 * later pages/modules of the project (e.g. the analytics dashboard) can
 * read it. sessionStorage clears when the tab closes — swap for
 * localStorage later if you want "stay logged in across browser restarts".
 */
function persistSession(token, role) {
  sessionStorage.setItem("wellness_token", token);
  sessionStorage.setItem("wellness_role", role);
}
