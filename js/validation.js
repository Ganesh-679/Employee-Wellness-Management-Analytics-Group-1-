/* =========================================================================
   validation.js
   -------------------------------------------------------------------------
   Pure, reusable validation helpers shared by every register/login page.
   Nothing in this file talks to a server — that's auth.js's job. Keeping
   validation separate from network calls makes both files easier to read
   and easier to test on their own.
   ========================================================================= */

/**
 * Checks an email address against a standard pattern.
 * This is a "good enough for the browser" check — the backend must
 * always re-validate, since client-side checks can be bypassed.
 */
function isValidEmail(email) {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return pattern.test(email.trim());
}

/**
 * Breaks a password down into the 5 rules the project brief asks for:
 * minimum length 8, at least one lowercase letter, one uppercase letter,
 * one digit, and one special character. Returns an object so the caller
 * can show which specific rule failed (instead of one vague "invalid").
 */
function getPasswordChecks(password) {
  return {
    length: password.length >= 8,
    lowercase: /[a-z]/.test(password),
    uppercase: /[A-Z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };
}

/** True only when every single rule above passes. */
function isPasswordValid(password) {
  const checks = getPasswordChecks(password);
  return Object.values(checks).every(Boolean);
}

/**
 * Turns the password checks into a rough 0-4 "strength" score, used only
 * to drive the visual strength meter. This is a UX nicety, not a security
 * boundary — isPasswordValid() above is what actually gates form submit.
 */
function getPasswordStrengthScore(password) {
  const checks = getPasswordChecks(password);
  let score = Object.values(checks).filter(Boolean).length;
  if (password.length >= 12) score += 1; // bonus for longer passwords
  return Math.min(score, 5);
}

/**
 * Wires up a password `<input>` so that, as the user types, a checklist
 * of <li data-rule="..."> elements gets a "met" class toggled, and an
 * optional strength meter container is updated.
 *
 * @param {HTMLInputElement} passwordInput
 * @param {HTMLElement|null} checklistEl   container with <li data-rule="length|lowercase|uppercase|number|special">
 * @param {HTMLElement|null} strengthEl    container with .bar elements + a .strength-label span
 */
function attachPasswordLiveFeedback(passwordInput, checklistEl, strengthEl) {
  passwordInput.addEventListener("input", () => {
    const checks = getPasswordChecks(passwordInput.value);

    if (checklistEl) {
      Object.keys(checks).forEach((rule) => {
        const li = checklistEl.querySelector(`[data-rule="${rule}"]`);
        if (li) li.classList.toggle("met", checks[rule]);
      });
    }

    if (strengthEl) {
      const score = getPasswordStrengthScore(passwordInput.value);
      strengthEl.classList.remove("strength-weak", "strength-medium", "strength-strong");
      const label = strengthEl.querySelector(".strength-label");

      if (passwordInput.value.length === 0) {
        if (label) label.textContent = "";
      } else if (score <= 2) {
        strengthEl.classList.add("strength-weak");
        if (label) label.textContent = "Weak password";
      } else if (score <= 4) {
        strengthEl.classList.add("strength-medium");
        if (label) label.textContent = "Medium strength";
      } else {
        strengthEl.classList.add("strength-strong");
        if (label) label.textContent = "Strong password";
      }
    }
  });
}

/**
 * Adds a click-to-toggle "show/hide password" eye button next to a
 * password input. Expects the button to sit inside the same
 * `.input-wrapper` as the input, with class `.toggle-eye`.
 */
function attachShowHideToggle(button, input) {
  button.addEventListener("click", () => {
    const nowVisible = input.type === "password";
    input.type = nowVisible ? "text" : "password";
    button.textContent = nowVisible ? "Hide" : "Show";
    button.setAttribute("aria-label", nowVisible ? "Hide password" : "Show password");
  });
}

/**
 * Shows or hides a small inline error message under a field, and toggles
 * a red/green border on the input itself.
 */
function setFieldError(input, errorEl, message) {
  if (message) {
    input.classList.add("field-invalid");
    input.classList.remove("field-valid");
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.classList.add("visible");
    }
  } else {
    input.classList.remove("field-invalid");
    input.classList.add("field-valid");
    if (errorEl) {
      errorEl.textContent = "";
      errorEl.classList.remove("visible");
    }
  }
}
