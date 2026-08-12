# API Endpoints — Login & Registration Module

The frontend is already wired to call these endpoints (see `js/auth.js`).
Build these on the backend (Flask, Node/Express, Django — whatever your
team picks) and the pages will work without any frontend changes.

Base URL used by the frontend: `http://localhost:5000/api`
(change `API_BASE_URL` in `js/auth.js` if your backend runs elsewhere).

All requests/responses are JSON. All endpoints are `POST`.

---

## 1. Employee registration

`POST /api/user/register`

Request:
```json
{
  "email": "priya@company.com",
  "password": "Wellness@123"
}
```

Success `201`:
```json
{ "message": "Account created successfully" }
```

Error `409` (email already registered):
```json
{ "message": "An account with this email already exists" }
```

Backend must **re-validate** the password rules (min 8 chars, upper,
lower, number, special char) — never trust the frontend alone. Hash the
password (e.g. bcrypt/argon2) before storing it. Never store plain text.

---

## 2. Admin registration

`POST /api/admin/register`

Request:
```json
{
  "adminId": "admin_priya01",
  "password": "Wellness@123"
}
```

Success `201`:
```json
{ "message": "Admin account created successfully" }
```

Error `409` (ID taken):
```json
{ "message": "This admin ID is already in use" }
```

---

## 3. Employee login

`POST /api/user/login`

Request:
```json
{
  "email": "priya@company.com",
  "password": "Wellness@123",
  "rememberMe": true
}
```

Success `200`:
```json
{
  "message": "Login successful",
  "token": "<JWT or session token>",
  "role": "user"
}
```

Error `401`:
```json
{ "message": "Invalid email or password" }
```

---

## 4. Admin login

`POST /api/admin/login`

Request:
```json
{
  "adminId": "admin_priya01",
  "password": "Wellness@123",
  "rememberMe": false
}
```

Success `200` / Error `401`: same shape as employee login above, with
`"role": "admin"`.

---

## 5. Request a password reset

`POST /api/forgot-password`

Request:
```json
{
  "identifier": "priya@company.com",
  "role": "user"
}
```
(`role` is `"user"` or `"admin"` — tells the backend which table to check.)

This is the **authentication check** step: the backend confirms an
account with that identifier exists, generates a short-lived one-time
code (OTP), stores it (with an expiry, e.g. 10 minutes), and emails it
to the registered address.

Success `200`:
```json
{ "message": "Verification code sent" }
```

Error `404` (no such account — consider always returning `200` in
production to avoid leaking which emails are registered):
```json
{ "message": "No account found with that identifier" }
```

---

## 6. Reset password

`POST /api/reset-password`

Request:
```json
{
  "identifier": "priya@company.com",
  "role": "user",
  "otp": "482913",
  "newPassword": "NewPass@456"
}
```

Backend checks the OTP matches and hasn't expired, re-validates the new
password rules, hashes it, and updates the stored record.

Success `200`:
```json
{ "message": "Password reset successfully" }
```

Error `400`:
```json
{ "message": "Invalid or expired verification code" }
```

---

## Suggested database schema

**users** (employees)
| column | type | notes |
|---|---|---|
| id | INT / UUID | primary key |
| email | VARCHAR, unique | login ID |
| password_hash | VARCHAR | bcrypt/argon2 hash, never plain text |
| created_at | TIMESTAMP | |

**admins**
| column | type | notes |
|---|---|---|
| id | INT / UUID | primary key |
| admin_id | VARCHAR, unique | login ID |
| password_hash | VARCHAR | |
| created_at | TIMESTAMP | |

**password_reset_tokens**
| column | type | notes |
|---|---|---|
| id | INT / UUID | primary key |
| identifier | VARCHAR | email or admin_id |
| role | VARCHAR | `"user"` or `"admin"` |
| otp_code | VARCHAR | the code sent to the user |
| expires_at | TIMESTAMP | e.g. 10 minutes after creation |
| used | BOOLEAN | prevents reusing the same code |

## Security notes for your backend

- Hash passwords with **bcrypt** or **argon2** — never store plain text.
- Re-run every password/email validation rule server-side too.
- Rate-limit `/login` and `/forgot-password` to slow down brute-force
  or spam attempts.
- Return the same generic error for "wrong password" and "no such
  account" on login, so attackers can't tell which emails are registered.
- Use HTTPS in production so credentials aren't sent in plain text.
