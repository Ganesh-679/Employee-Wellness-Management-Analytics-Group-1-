# Employee Wellness Management — Backend (Login & Registration)

Flask backend built to match the frontend's `API_ENDPOINTS.md` exactly —
no frontend changes needed, just point `API_BASE_URL` in `js/auth.js` at
this server (default already matches: `http://localhost:5000/api`).

## Tech stack
- Flask + Flask-SQLAlchemy (SQLite by default, swap to MySQL/Postgres later)
- Flask-Bcrypt — password hashing
- Flask-JWT-Extended — login tokens
- Flask-Limiter — rate limits login/forgot-password against brute force
- Flask-CORS — lets the frontend call this API from a different origin

## Setup

```bash
cd wellness_backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Runs at `http://localhost:5000`. Tables auto-create in `wellness.db` on
first run.

### Connecting to the team's shared database (Aditya's SQLite setup)
This project now uses SQLite end to end (per your mentor's instruction) —
no separate database server needed. To use the exact same database file
Aditya's schema creates:

1. Get Aditya's `setup_db.py` + `schema.sql` and place them in this same
   folder (the project root).
2. Run his setup script once — creates `wellness.db` with all 3 tables:
   ```bash
   python3 setup_db.py
   ```
3. Copy `.env.example` (included here) to `.env` — it already matches his
   `DB_FILE=wellness.db` format, so no editing needed unless he renames
   the file.
4. Run `python3 app.py` **from this same folder** — it'll read/write the
   exact same `wellness.db` file, no code changes needed.

If no `.env` file is present, the backend falls back to creating its own
local `wellness.db`, so it still runs standalone for quick testing.

> **Important:** both `setup_db.py` and `app.py` must be run from the same
> folder (the one containing `wellness.db`), since SQLite paths are
> relative to wherever you launch the script from.

### Sending real OTP emails
By default, forgot-password OTPs are just printed to the console/log
(look for `[DEV] OTP for ...`) so you can test the flow without a mail
server. To actually send emails, set these env vars:
```bash
export MAIL_SERVER=smtp.gmail.com
export MAIL_PORT=587
export MAIL_USERNAME=your_email@gmail.com
export MAIL_PASSWORD=your_app_password
export MAIL_SENDER=your_email@gmail.com
```

## Endpoints (matches API_ENDPOINTS.md)

| Method | Endpoint | Body | Notes |
|---|---|---|---|
| POST | `/api/user/register` | `{email, password}` | 201 / 409 if email taken |
| POST | `/api/admin/register` | `{adminId, password}` | 201 / 409 if ID taken |
| POST | `/api/user/login` | `{email, password, rememberMe}` | 200 + token / 401 |
| POST | `/api/admin/login` | `{adminId, password, rememberMe}` | 200 + token / 401 |
| POST | `/api/forgot-password` | `{identifier, role}` | sends OTP, 200 / 404 |
| POST | `/api/reset-password` | `{identifier, role, otp, newPassword}` | 200 / 400 |
| GET | `/api/health` | — | quick server check |

Password rules (enforced server-side, mirrors `js/validation.js`):
min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character.

`rememberMe: true` issues a 30-day token instead of the default 8-hour one.

## Project structure
```
wellness_backend/
├── app.py                    # App factory, blueprint registration, entry point
├── config.py                 # DB URL, secrets, JWT/OTP expiry, mail settings
├── extensions.py              # db, bcrypt, jwt, cors, limiter instances
├── models.py                  # User, Admin, PasswordResetToken
├── utils.py                    # Email/password validation, OTP generation + sending
├── routes/
│   ├── user.py                 # /api/user/register, /api/user/login
│   ├── admin.py                 # /api/admin/register, /api/admin/login
│   └── password_reset.py        # /api/forgot-password, /api/reset-password
└── requirements.txt
```

## Tested end-to-end
Registration (valid + weak password + duplicate), login (correct + wrong
password), admin register/login, and the full forgot → OTP → reset →
login-with-new-password cycle including OTP reuse rejection — all
verified against a running instance before handing this off.

## Notes for your team
- **CORS** is wide open (`origins: "*"`) for dev convenience — restrict
  this to the deployed frontend's actual URL before production.
- **Admin OTP delivery**: `adminId` isn't necessarily an email, so admin
  OTPs currently just print to the console. Flag this to your team —
  admins probably need a linked email on file to actually receive codes.
- **Rate limiting** uses in-memory storage, fine for one dev server; if
  you deploy with multiple workers, back it with Redis instead.
