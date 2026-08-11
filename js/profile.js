/* =========================================================================
   profile.js
   -------------------------------------------------------------------------
   Personal Information section (part of Module 1). Uses the same
   healthApiRequest() helper defined in health.js.
   ========================================================================= */

function getProfile(token) {
  return healthApiRequest("/profile", { method: "GET", token });
}

function saveProfile(payload, token) {
  return healthApiRequest("/profile", { method: "PUT", body: payload, token });
}
