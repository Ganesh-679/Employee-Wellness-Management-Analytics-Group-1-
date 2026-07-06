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
# WellSpring Analytics — Login & Registration Module

Employee Wellness Management Analytics · Infosys Springboard AIML Internship

This is Module 1 of the project: the login/registration frontend. It's
plain **HTML, CSS, and JavaScript** — no frameworks, no build step — so
you can open it directly in a browser or serve it with any static server.

---

## 1. What's in this folder

```
project/
├── index.html              Home page — Sign Up / Sign In choice
├── signup.html              Choose Employee or Admin registration
├── register-user.html       Employee registration form
├── register-admin.html      Admin registration form
├── login.html                Choose Employee or Admin login
├── login-user.html           Employee login form
├── login-admin.html          Admin login form
├── forgot-password.html      Shared forgot-password flow (both roles)
├── css/
│   └── style.css             All styling — colors, layout, components
├── js/
│   ├── validation.js         Email/password rule checking, live UI feedback
│   └── auth.js               Talks to the backend (fetch calls, toasts)
├── API_ENDPOINTS.md          Backend contract + suggested DB schema
└── README.md                 You are here
```

## 2. How the pages connect (the flow)

```
index.html
 ├── "Create an account" → signup.html
 │        ├── Employee → register-user.html  ─┐
 │        └── Admin    → register-admin.html ─┴──► login.html
 └── "Sign in" → login.html
          ├── Employee → login-user.html  → forgot-password.html?role=user
          └── Admin    → login-admin.html → forgot-password.html?role=admin
```

Every page is a real `.html` file, and links between them are plain
`<a href="...">` tags — that's why there's no build tool. Right-click any
link text in the code and you'll find exactly where it goes.

## 3. How the code works, section by section

### `css/style.css`
Every color and font is defined once at the top as a **CSS variable**
(e.g. `--teal-700: #1b5e56;`). All the components below reference those
variables instead of hardcoded colors, so you can re-theme the whole app
by editing a handful of lines at the top of the file. The file is split
into clearly commented sections: tokens → reset → layout shell →
signature graphic → components (buttons, forms, checklist, toasts) →
responsive rules.

### `js/validation.js`
This file has **no network calls at all** — it only checks whether an
email/password *looks* valid, and updates the on-screen checklist and
strength meter as you type. Key functions:
- `isValidEmail(email)` — regex check for a valid email shape.
- `getPasswordChecks(password)` — returns `{length, lowercase, uppercase, number, special}` booleans.
- `isPasswordValid(password)` — true only if every rule above passes.
- `attachPasswordLiveFeedback(...)` — listens for typing and updates the checklist/strength bar live.
- `attachShowHideToggle(...)` — powers the "Show/Hide" button next to password fields.

### `js/auth.js`
This file is where the frontend would talk to your backend. Right now
there's no backend yet, so calling these functions will show a friendly
"Couldn't reach the server" error — that's expected until Module 2 is
built. Key pieces:
- `API_BASE_URL` — change this one line once your backend has a real address.
- `apiRequest(path, body)` — a shared `fetch()` wrapper so every call handles JSON and errors the same way.
- `registerUser`, `registerAdmin`, `loginUser`, `loginAdmin`, `requestPasswordReset`, `resetPassword` — one function per backend endpoint, matching `API_ENDPOINTS.md`.
- `showToast(message, type)` — the small pop-up notification in the corner.
- `setButtonLoading(button, isLoading)` — shows a spinner and disables the button while a request is in flight, so users can't double-submit.

### Each HTML page's `<script>` block
Every register/login page follows the same pattern at the bottom of the
file:
1. Grab the form and input elements with `document.getElementById(...)`.
2. Wire up live validation (`attachPasswordLiveFeedback`, blur checks).
3. Listen for the form's `submit` event, call `event.preventDefault()`
   so the browser doesn't reload the page.
4. Re-check every rule (never trust that step 2 already caught it).
5. Call the matching `auth.js` function, show a toast, and redirect on success.

## 4. Default enhancements already built in

- Live password checklist (✓ turns green as each rule is met)
- Password strength meter (weak / medium / strong)
- Show/Hide password toggle on every password field
- Inline field errors instead of blocking `alert()` popups
- Toast notifications for success/failure
- "Remember me" checkbox on both login pages
- A loading spinner inside buttons while a request is pending, so users get feedback instead of wondering if their click worked
- Keyboard focus is visible everywhere (accessibility)
- Fully responsive — the side brand panel stacks on top on mobile

## 5. Opening and running this in VS Code

1. **Install VS Code** if you don't have it: https://code.visualstudio.com
2. **Open the folder**: `File → Open Folder...` → select the `project` folder.
3. **Install the "Live Server" extension** (by Ritwick Dey) from the
   Extensions panel (the icon that looks like four squares on the left
   sidebar, or `Ctrl+Shift+X` / `Cmd+Shift+X`). Search "Live Server" → Install.
4. **Run it**: right-click `index.html` in the file explorer → "Open with Live Server".
   Your browser opens automatically at something like `http://127.0.0.1:5500`.
5. Click around — Sign Up → Employee/Admin → fill the form → it will
   currently show a "Couldn't reach the server" toast, which is correct,
   since there's no backend yet. All the validation, styling, and page
   navigation already works without one.

Once your teammates build the backend from `API_ENDPOINTS.md`, update
`API_BASE_URL` in `js/auth.js` to point at it, and every form will start
working end-to-end.

## 6. Deploying this to GitHub

### First time: create the repository
1. Go to https://github.com and log in.
2. Click the **+** icon (top right) → **New repository**.
3. Name it something like `wellness-login-module`. Leave it **Public** or
   **Private** as your internship requires. Don't check "Add a README" (you already have one).
4. Click **Create repository** — GitHub will show you a page with setup commands; keep that tab open.

### Push your code from VS Code
Open the built-in terminal in VS Code: `` Terminal → New Terminal `` (or `` Ctrl+` ``), then run these one at a time, inside your `project` folder:

```bash
git init
git add .
git commit -m "Add login and registration module"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/wellness-login-module.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your actual GitHub username (and the repo
name if you called it something else — copy the exact URL from the page
GitHub showed you in step 4 above).

If this is your first time using Git on this machine, it may ask you to
configure your identity first — run these once, with your own details:
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Publishing it as a live website (optional, free)
Since this is a static site (no backend needed to view the pages), you
can turn it on with GitHub Pages:
1. On your repo's GitHub page, go to **Settings → Pages**.
2. Under "Build and deployment", set **Source** to **Deploy from a branch**.
3. Pick branch `main`, folder `/ (root)`, then **Save**.
4. Wait about a minute, then refresh — GitHub gives you a live URL like
   `https://YOUR-USERNAME.github.io/wellness-login-module/`.

Note: GitHub Pages only serves the frontend files — the "Sign up"/"Sign
in" buttons won't successfully create accounts until your backend
(Module 2) is deployed somewhere reachable too, and `API_BASE_URL` in
`js/auth.js` points at it.

### Making changes later
Every time you edit files, save, and want to update GitHub:
```bash
git add .
git commit -m "Describe what you changed"
git push
```

## 7. Suggested next steps for your internship project

- Build the backend endpoints in `API_ENDPOINTS.md` (Flask is a common
  choice for AIML-track interns since your project likely also uses
  Python for the analytics side).
- Set up the database tables from the schema in `API_ENDPOINTS.md`.
- Add real email sending for the forgot-password OTP (e.g. via an SMTP
  service) once the backend exists.
- After login succeeds, build `dashboard.html` (employee) and
  `admin-dashboard.html` (admin) — the next module of your project.
