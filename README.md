# 🎓 BracU Course Combinator

> An intelligent schedule planner and conflict-free combination generator for BRAC University students.

Works across **Web App (Modern Browser UI)**, **Desktop GUI (Tkinter)**, and **Command Line Interface (CLI)**.

---

## 🌟 Available Formats

| Interface | Description | How to Run |
| :--- | :--- | :--- |
| **🌐 Web App** | Modern responsive website with visual timetable cards, autocomplete, and PDF/CSV export | Double-click `run_web.bat` (Windows) or `./run_web.sh` (Mac/Linux) |
| **🖥️ Desktop GUI** | Standalone native desktop window | Double-click `run.bat` (Windows) or `./run.sh` (Mac/Linux) |
| **⌨️ CLI Tool** | Terminal command for power users and automation scripts | `python schedule_combinator.py CSE110 MAT110` |

---

## 🚀 Quick Start: Web App

### **Windows**
Double-click `run_web.bat`.  
*(It will automatically configure Python virtual environment, install dependencies, and launch `http://localhost:8000` in your browser).*

### **macOS / Linux**
```bash
./run_web.sh
```

### **Manual Launch**
```bash
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)**.

---

## ☁️ Free Cloud Deployment (Deploy Online)

Want to host this website on the internet so your friends can use it from anywhere without installing Python?

1. Push this repository to GitHub.
2. Go to **[Render.com](https://render.com)** $\rightarrow$ **New Web Service** $\rightarrow$ select your repo.
3. Render automatically detects `render.yaml` and deploys your free live website!
*(See [WEB_GUIDE.md](WEB_GUIDE.md) for step-by-step instructions on Render, Railway, and Hugging Face Spaces).*

---

## ✨ Key Features

- **Conflict-Free Guarantee**: Checks theory classes, labs, and final exam slots to eliminate all clashes.
- **Interactive Visual Timetable Grid**: 7-day visual schedule with color-coded course blocks, distinguishing Lectures and Labs.
- **Live Search & Autocomplete**: Real-time course suggestions from the live USIS feed (over 2,000+ course sections).
- **Seat Availability Filter**: Toggle to only show sections with open seats.
- **Day Count & Gap Optimization**: Target a specific number of class days per week and sort for the most compact schedules (minimum campus idle time).
- **Mandatory Section Locks**: Lock specific sections for courses (e.g., `CSE110:01`).
- **Faculty Preferences & Avoidance**: Rank preferred faculty higher or hard-filter out avoided instructors.
- **Skip Time Rules**: Avoid morning 8:00 AM or late evening slots.
- **One-Click Exports**: Download multi-page PDF schedule reports or CSV spreadsheets.
- **Dark / Light Theme**: Built-in responsive theme with keyboard shortcuts (`←` and `→` arrow keys to navigate schedules).
