# WellSpring Analytics — Backend Development & DB Integration Guide

This guide is for the backend development team. It explains how to set up the PostgreSQL database locally and lists the API specifications and business logic required to connect the frontend pages to the database.

---

## 1. Local Database Setup

To set up the database on your local machine, follow these steps:

1. **Install dependencies**:
   Run the following command to install the required PostgreSQL Python driver and env helper:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your environment**:
   * Copy the template file `.env.example` to a new file named `.env`.
   * Open `.env` and fill in your local PostgreSQL username, port, and password:
     ```env
     DB_HOST=localhost
     DB_PORT=5432
     DB_USER=postgres
     DB_PASSWORD=your_actual_postgres_password
     DB_NAME=wellness_db
     ```

3. **Initialize the Database**:
   Run the automatic setup script:
   ```bash
   python setup_db.py
   ```
   This script will connect to your local PostgreSQL instance, create the `wellness_db` database if it doesn't exist, and build all the required tables and indexes.

---

## 2. Database Schema Reference

The tables created in the database are:

### `users` (Employees)
| Column | PostgreSQL Type | Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier |
| `email` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` | User's work email |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Hashed password (never plain text) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Signup timestamp |

### `admins` (Administrators)
| Column | PostgreSQL Type | Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier |
| `admin_id` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` | Admin's login ID |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Hashed password (never plain text) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Signup timestamp |

### `password_reset_tokens` (OTP codes)
| Column | PostgreSQL Type | Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier |
| `identifier` | `VARCHAR(255)` | `NOT NULL` | Email or Admin ID |
| `role` | `VARCHAR(50)` | `NOT NULL` (Value must be `'user'` or `'admin'`) | Identifies which table to check |
| `otp_code` | `VARCHAR(10)` | `NOT NULL` | One-time code sent to user |
| `expires_at` | `TIMESTAMP` | `NOT NULL` | Code expiration time (e.g. +10 mins) |
| `used` | `BOOLEAN` | `DEFAULT FALSE` | Prevents code reuse |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Generation timestamp |

---

## 3. Required API Endpoints to Implement

The frontend makes JSON POST requests to `http://localhost:5000/api`. Your backend server should handle the following routes:

### 1. Employee Registration
`POST /api/user/register`
* **Payload**: `{ "email": "user@company.com", "password": "UserPass@123" }`
* **Logic**:
  1. Validate email structure and password strength (server-side check).
  2. Check if email already exists in the `users` table. If it does, return `409 Conflict` (`{ "message": "An account with this email already exists" }`).
  3. Hash the password using a secure library (e.g. `bcrypt`).
  4. Insert the record into the `users` table.
* **Success Response**: `201 Created` (`{ "message": "Account created successfully" }`)

### 2. Admin Registration
`POST /api/admin/register`
* **Payload**: `{ "adminId": "admin_username", "password": "AdminPass@123" }`
* **Logic**:
  1. Check if `adminId` already exists in `admins` table. If it does, return `409 Conflict` (`{ "message": "This admin ID is already in use" }`).
  2. Hash the password using `bcrypt`.
  3. Insert the record into the `admins` table.
* **Success Response**: `201 Created` (`{ "message": "Admin account created successfully" }`)

### 3. Employee Login
`POST /api/user/login`
* **Payload**: `{ "email": "user@company.com", "password": "UserPass@123", "rememberMe": true }`
* **Logic**:
  1. Fetch the user record by `email` from the `users` table.
  2. Compare the payload password with the stored `password_hash` using `bcrypt.checkpw` (or equivalent).
  3. If user doesn't exist or password mismatch, return `401 Unauthorized` (`{ "message": "Invalid email or password" }`).
  4. If matches, generate a session/JWT token.
* **Success Response**: `200 OK` (`{ "message": "Login successful", "token": "<JWT_token>", "role": "user" }`)

### 4. Admin Login
`POST /api/admin/login`
* **Payload**: `{ "adminId": "admin_username", "password": "AdminPass@123", "rememberMe": false }`
* **Logic**:
  1. Fetch the admin record by `admin_id` from the `admins` table.
  2. Verify the password. If invalid, return `401 Unauthorized` (`{ "message": "Invalid admin ID or password" }`).
  3. Generate a session/JWT token.
* **Success Response**: `200 OK` (`{ "message": "Login successful", "token": "<JWT_token>", "role": "admin" }`)

### 5. Forgot Password Request
`POST /api/forgot-password`
* **Payload**: `{ "identifier": "user@company.com", "role": "user" }`
* **Logic**:
  1. Depending on `role` (`user` or `admin`), check if the `identifier` exists in the corresponding table.
  2. If it doesn't, return `404 Not Found` (`{ "message": "No account found with that identifier" }`).
  3. Generate a 6-digit random verification code (OTP).
  4. Store the OTP in `password_reset_tokens` with an expiration timestamp (e.g. +10 minutes).
  5. Send the OTP code to the user (e.g. print it to console in development, send via SMTP in production).
* **Success Response**: `200 OK` (`{ "message": "Verification code sent" }`)

### 6. Reset Password
`POST /api/reset-password`
* **Payload**: `{ "identifier": "user@company.com", "role": "user", "otp": "123456", "newPassword": "NewPassword@123" }`
* **Logic**:
  1. Query `password_reset_tokens` for the newest, unused token matching the `identifier` and `role`.
  2. Verify if the token matches `otp` and `expires_at > CURRENT_TIMESTAMP`. If expired/used/wrong, return `400 Bad Request` (`{ "message": "Invalid or expired verification code" }`).
  3. Hash `newPassword` and update the record in the `users` or `admins` table.
  4. Mark the token as `used = TRUE` in the `password_reset_tokens` table.
* **Success Response**: `200 OK` (`{ "message": "Password reset successfully" }`)

---

## 4. Key Security Implementation Notes

1. **Password Security**: Never write or store passwords in plain text. Always run passwords through a robust hashing function like **bcrypt** or **argon2** before inserting them.
2. **CORS Configuration**: Since the frontend is run via `file://` or a separate static server (e.g., Live Server on `http://127.0.0.1:5500`), ensure **CORS** (Cross-Origin Resource Sharing) is enabled in your backend framework (e.g., `flask-cors` for Python Flask or `cors` middleware for Node.js Express).
3. **Validation Double-check**: The frontend validates input, but client-side checks can be bypassed. Ensure your backend re-validates the fields (email format, password complexity rules).
