# 🌿 Employee Wellness & Health Analytics System

A comprehensive, full-stack **Employee Wellness Management and Health Analytics Platform** powered by Python, Flask, SQLAlchemy, custom Natural Language Processing (NLP) sentiment scoring, and modern interactive UI dashboards.

---

## 🌟 Key Features & Modules

### 🔐 Module 1: Authentication & Role-Based Access Control (RBAC)
- **Dual Portal Access**: Dedicated login interfaces for **Employees** and **HR Admins**.
- **Secure Authentication**: Built using **JWT (JSON Web Tokens)** and **BCrypt** password hashing.
- **Rate Limiting**: Integrated **Flask-Limiter** to prevent brute-force attacks.

---

### 📊 Module 2: Employee Health Profiling & Risk Assessment
- **Dynamic Vitals Logging**: Record BMI, Systolic/Diastolic Blood Pressure, Heart Rate, Glucose, and Lifestyle indicators.
- **Automated Risk Tiering**: Algorithmic assessment categorizing employee health into **Low**, **Moderate**, **High**, or **Critical** risk tiers.
- **Personalized Action Plans**: Intelligent recommendation engine delivering tailored nutrition, fitness, lifestyle, and mental wellness suggestions.

---

### 🛡️ Module 3: HR Admin Management & Analytics
- **Executive Analytics Dashboard**: Real-time aggregate overview of organizational health trends and risk distributions.
- **Departmental Heatmaps**: Compare average health risks and participation across business units (*Engineering, Sales, HR, Operations, etc.*).
- **Offboarding Management**: Secure employee offboarding with cascade record scrubbing.
- **Anonymized Action Center**: Early warning alerts flagging elevated health and stress risks.

---

### 🧠 Module 4: Mental Health & Sentiment Analytics Engine
- **Custom Rule-Based NLP Scorer**: Natural language engine analyzing journal reflections with **3-word negation lookback** (e.g. accurately parsing *"not stressed"* or *"no deadlines or pressure"*).
- **Multi-Dimensional Metrics**: Computes **Sentiment Polarity** (`-1.0` to `+1.0`), **Stress Probability**, **Anxiety Probability**, and **Burnout Risk**.
- **Emotion Tag Detection**: Identifies state tags (*Motivated, Calm, Happy, Burned Out, Stressed, Anxious, Tired*).
- **Interactive Visual Gauges & Polarity Bar**: Circular SVG progress dials, dynamic visual gradient fill bar with a glowing slider pointer handle, and expressive sentiment emojis (`😁`, `😊`, `😐`, `😟`, `😫`).
- **Trend Visualization**: Interactive **Chart.js** historical sentiment tracking line graphs.
- **HR Admin Wellbeing Panel**: Anonymized organizational mood indices and department burnout alert maps.

---

## 🏗️ Tech Stack

### **Backend**
- **Language**: Python 3.10+
- **Framework**: Flask
- **Database**: SQLite3 with **SQLAlchemy ORM** & raw `schema.sql` fallbacks
- **Security & Tokens**: Flask-JWT-Extended, Flask-BCrypt, Flask-Limiter
- **Analytics**: Scikit-Learn, NumPy, Custom Lexicon NLP Engine

### **Frontend**
- **Core**: HTML5, Vanilla JavaScript (ES6+), CSS3
- **Design System**: Glassmorphism UI theme, CSS Variables, Light/Dark Mode switching
- **Data Visualization**: Chart.js, Custom Animated SVG Gauges

---

## 📂 Project Structure

```text
wellness/
├── app.py                   # Flask Application Factory & Blueprint Registration
├── config.py                # Environment Configuration & Secret Keys
├── extensions.py            # Centralized Database, JWT & Security Extensions
├── models.py                # SQLAlchemy Database Models (User, HealthRecord, SentimentLog, etc.)
├── schema.sql               # Pure SQL Table Initialization Scripts
├── utils.py                 # Health Risk Algorithms, Diet/Fitness Scorer & Custom NLP Engine
│
├── routes/                  # Modular Route Blueprints
│   ├── auth.py              # User Registration & Login Endpoints
│   ├── employee.py          # Employee Profile & Health Vitals Endpoints
│   ├── admin.py             # HR Admin Dashboard & Employee Offboarding Endpoints
│   └── sentiment.py         # Mental Health Sentiment Analysis & History Endpoints
│
├── dashboard.html           # Interactive Employee Wellness Hub UI
├── admin-dashboard.html     # HR Executive Analytics & Mental Health Dashboard UI
├── login.html               # Employee Authentication UI
├── login-admin.html         # HR Admin Authentication UI
└── register.html            # User Registration Portal UI
```

---

## ⚙️ Installation & Local Setup

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Clone Repository
```bash
git clone https://github.com/Gowthamsai1234/Employee_wellness_management_analytics.git
cd Employee_wellness_management_analytics
```

### 3. Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Initialize Database & Run Server
```bash
python app.py
```
The server will start locally at **`http://127.0.0.1:5000`**.

---

## 🔒 API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register a new employee account |
| `POST` | `/api/auth/login` | Authenticate employee & return JWT token |
| `POST` | `/api/admin/login` | Authenticate HR Admin & return JWT token |
| `GET` | `/api/employee/dashboard` | Fetch employee vitals & personalized recommendations |
| `POST` | `/api/employee/health-log` | Log new health vitals & recalculate risk tier |
| `POST` | `/api/sentiment/analyze` | Submit journal reflection for NLP sentiment analysis |
| `GET` | `/api/sentiment/history` | Retrieve historical sentiment logs for trend plotting |
| `GET` | `/api/sentiment/dashboard-summary` | Fetch latest employee sentiment KPIs & averages |
| `GET` | `/api/admin/dashboard` | Fetch aggregate org health, sentiment & department stats |
| `DELETE` | `/api/admin/employees/<id>` | Offboard employee & scrub linked records |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

---

## 📜 License

This project is open source and available under the [MIT License](LICENSE).
