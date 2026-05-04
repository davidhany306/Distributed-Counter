# 📡 Distributed Systems Project

## 📖 Overview

This project demonstrates two distributed systems built with Python, showcasing **client-server architecture**, **thread synchronization**, and **real-time communication**:

1. **Distributed Counter System**  
   A shared counter that multiple clients can increment, decrement, reset, or query over TCP.

2. **Distributed Attendance System**  
   A full-stack attendance tracking system with:
   - Student check-in (Streamlit UI)
   - Admin dashboard
   - Persistent database (SQLite)
   - Real-time server communication

Both systems use **multithreading and locks** to safely handle concurrent users.

---

## 🚀 Features

### 🔒 Core Concepts
- Thread-safe operations using `threading.Lock`
- TCP socket communication
- Multi-client support (concurrent connections)
- Client-server architecture

---

### 🔢 Distributed Counter System
- Increment / Decrement / Reset / Get counter
- Multiple clients supported
- Console client for testing
- Demonstrates race condition handling

---

### 📋 Distributed Attendance System
- 🎓 Student attendance submission (ID + Name)
- 🛡️ Admin dashboard (secure login)
- 📊 Group-based tracking (Lectures & Tutorials)
- 📁 CSV export (per group or all groups)
- 🔍 Search functionality (admin)
- 📈 Live capacity tracking
- 💾 Persistent storage using SQLite
- 🚫 Duplicate prevention (same student per day)
- ⚡ Real-time server validation

---

## 🏗️ Architecture

```
[ Client (Streamlit / Console) ]
                │
                ▼
        TCP Socket Server
                │
                ▼
         SQLite Database
```

- Each client connects via TCP  
- Server spawns a **thread per client**  
- Database ensures **data persistence**  
- Lock ensures **safe concurrent writes**

---

## ⚙️ Requirements

- Python 3.7+
- Streamlit

Install dependencies:
```bash
pip install streamlit
```

---

## 🛠️ Installation

```bash
git clone <your-repo-url>
cd distributed-systems-project
```

---

## ▶️ Usage

### 🔢 Run Distributed Counter System

#### Start Server
```bash
python server.py
```

#### Run Client
```bash
python client.py
```

Commands:
```
INCREMENT
DECREMENT
RESET
GET
```

---

### 📋 Run Attendance System

#### 1. Start Server
```bash
python server.py
```

#### 2. Start Web App
```bash
streamlit run app.py
```

Open in browser:
```
http://localhost:8501
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

| Variable | Default | Description |
|----------|--------|------------|
| ATTEND_HOST | 127.0.0.1 | Server host |
| ATTEND_PORT | 5000 | Server port |
| ATTEND_CAPACITY | 40 | Max students per group |
| ATTEND_ADMIN_USER | admin | Admin username |
| ATTEND_ADMIN_PASS | 1234 | Admin password |

---

## 📡 Server Commands (Attendance)

| Command | Description |
|--------|------------|
| `MARK:group:id:name` | Mark attendance |
| `GET:group` | Get today’s count |
| `ADMIN:group:date` | Get attendance list |
| `SUMMARY:date` | Get all groups summary |

---

## 🗄️ Database

- File: `attendance.db`
- Uses SQLite for persistence

Table structure:
```sql
attendance(
    id INTEGER PRIMARY KEY,
    grp TEXT,
    sid TEXT,
    name TEXT,
    date TEXT
)
```

Unique constraint prevents duplicates:
```
(group, sid, date)
```

---

## ⚠️ Concurrency Handling

Without locks:
```
Thread A reads value = 5
Thread B reads value = 5
Thread A writes 6
Thread B writes 6  ❌ (lost update)
```

With locks:
```python
with lock:
    # safe operation
```

✔ Ensures correct results under heavy load

---

## 📁 Project Structure

| File | Description |
|------|-------------|
| `server.py` | Counter + Attendance TCP server |
| `client.py` | Counter console client |
| `app.py` | Streamlit attendance system |

---

## 💡 Future Improvements

- User authentication system (database-based)
- Docker deployment
- Mobile-friendly UI
- QR code attendance
- Analytics dashboard

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Add new features
- Improve UI
- Optimize performance

---

## 📄 License

MIT License
