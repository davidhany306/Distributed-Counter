# 📋 Distributed Attendance System

## 📖 Overview

This project is a **distributed attendance tracking system** built using Python.
It demonstrates key distributed systems concepts such as:

* Client-server architecture (TCP sockets)
* Multithreading & synchronization
* Real-time communication
* Persistent storage with SQLite
* Web-based user interface using Streamlit

The system allows students to mark attendance and admins to monitor, search, and export records.

---

## 🚀 Features

### 🎓 Student Features

* Mark attendance using **Student ID + Name**
* Select lecture/tutorial group
* Prevent duplicate attendance (same day)
* Real-time validation with server
* Live capacity tracking

### 🛡️ Admin Features

* Secure login system
* View attendance per group
* View all groups summary
* Filter by date
* Export attendance as CSV
* Search by name or ID

---

## 🏗️ Architecture

```
[ Streamlit App (app.py) ]
                │
                ▼
        TCP Socket Server (server.py)
                │
                ▼
        SQLite Database (attendance.db)
```

* The **client (Streamlit app)** communicates with the server via TCP sockets
* The **server handles multiple clients** using threads
* The **database ensures data persistence**
* Locks ensure **safe concurrent operations**

---

## ⚙️ Requirements

* Python 3.7+
* Streamlit

Install dependencies:

```bash
pip install streamlit
```

---

## 🛠️ Installation

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

---

## ▶️ Usage

### 1. Start the Server

```bash
python server.py
```

---

### 2. Run the Web App

```bash
streamlit run app.py
```

Open in your browser:

```
http://localhost:8501
```

---

### 3. (Optional) Run Console Client

```bash
python client.py
```

---

## 🔐 Admin Login

Default credentials:

```
Username: admin
Password: 1234
```

You can change them using environment variables:

```bash
export ATTEND_ADMIN_USER=your_user
export ATTEND_ADMIN_PASS=your_pass
```

---

## 🌍 Environment Variables

| Variable          | Default   | Description            |
| ----------------- | --------- | ---------------------- |
| ATTEND_HOST       | 127.0.0.1 | Server host            |
| ATTEND_PORT       | 5000      | Server port            |
| ATTEND_CAPACITY   | 40        | Max students per group |
| ATTEND_ADMIN_USER | admin     | Admin username         |
| ATTEND_ADMIN_PASS | 1234      | Admin password         |

---

## 📡 Server Commands

| Command            | Description                  |
| ------------------ | ---------------------------- |
| MARK:group:id:name | Mark attendance              |
| GET:group          | Get today's attendance count |
| ADMIN:group:date   | Get attendance list          |
| SUMMARY:date       | Get all groups summary       |

---

## 🗄️ Database

* File: `attendance.db`
* Database: SQLite

### Table Structure:

```sql
attendance(
    id INTEGER PRIMARY KEY,
    grp TEXT,
    sid TEXT,
    name TEXT,
    date TEXT
)
```

### Constraint:

* Prevents duplicate attendance:

```
(group, sid, date)
```

---

## ⚠️ Concurrency Handling

Without locks:

```
Thread A reads value
Thread B reads value
Thread A writes
Thread B overwrites ❌
```

With locks:

```python
with lock:
    # safe database operation
```

✔ Ensures correct behavior with multiple users

---

## 📁 Project Structure

| File        | Description                         |
| ----------- | ----------------------------------- |
| `server.py` | TCP server handling attendance      |
| `app.py`    | Streamlit web interface             |
| `client.py` | Optional console client for testing |

---

## 💡 Future Improvements

* Authentication system with database
* QR code attendance
* Mobile-friendly UI
* Docker deployment
* Analytics dashboard

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

* Improve UI
* Add features
* Optimize performance


