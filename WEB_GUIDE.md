# 🌐 Course Combinator Web App Guide

A modern, responsive, full-featured web application for the **BracU Course Combinator**. It provides a reactive UI with interactive timetable grids, live course search & auto-complete, seat indicators, section inspector modals, and one-click PDF/CSV schedule exports.

---

## 🚀 1. How to Run Locally

### **On Windows (1-Click)**
1. Double-click `run_web.bat`.
2. It will automatically check Python, create a virtual environment, install requirements, and open your browser at `http://localhost:8000`.

### **On macOS / Linux (1-Click)**
1. Open Terminal in the project directory and run:
   ```bash
   ./run_web.sh
   ```
2. It automatically starts the server and opens `http://localhost:8000`.

### **Manual Run via Terminal / Command Prompt**
```bash
# 1. Activate your virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install requirements
pip install -r requirements.txt

# 3. Start the web server
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 📡 2. Share with Friends on the Same Wi-Fi (Local Network)

To let friends or roommates on the same Wi-Fi access your running web app from their laptops or phones:

1. Start Uvicorn bound to `0.0.0.0`:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
2. Find your local IP address:
   - **Windows**: run `ipconfig` (look for *IPv4 Address*, e.g., `192.168.0.105`).
   - **macOS/Linux**: run `ifconfig` or `ipconfig getifaddr en0`.
3. Share the URL with anyone connected to your Wi-Fi:
   ```
   http://192.168.0.105:8000
   ```

---

## ☁️ 3. How to Host on the Internet for Free (Deploy Online)

Deploying online allows anyone in the world to open your website without installing Python!

### **Option A: Render.com (Recommended - 100% Free & 1-Click)**
1. Push this project folder to a GitHub repository (e.g. `github.com/your-username/course-combinator-web`).
2. Go to [Render.com](https://render.com) and create a free account.
3. Click **New +** $\rightarrow$ **Web Service** $\rightarrow$ connect your GitHub repository.
4. Render will automatically detect `render.yaml` and `requirements.txt`:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service**. Your website will be live at `https://your-app-name.onrender.com` in 2 minutes!

---

### **Option B: Railway.app (Free Tier)**
1. Go to [Railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Railway automatically detects the `Dockerfile` and `Procfile` and launches the website with a free live URL!

---

### **Option C: Hugging Face Spaces (Free Cloud Hosting with 16GB RAM)**
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces).
2. Click **Create new Space** $\rightarrow$ select **Docker** or **Gradio/FastAPI**.
3. Push your code or upload the files.
4. Hugging Face builds and hosts your app instantly on their global cloud!

---

## ✨ Features in the Web App

* ⚡ **Live Auto-complete Search**: Search from over 2,000+ course sections with live faculty and seat status.
* 📅 **Interactive Visual Timetable Grid**: 7-day visual schedule with color-coded courses, distinguishing Lecture vs Lab.
* 🔄 **Pagination & Keyboard Navigation**: Use `< Prev` and `Next >` or the **Left/Right Arrow keys** to flip through all conflict-free schedules.
* 🔍 **Course Section Inspector**: Click the info icon on any course to preview all available sections, faculties, and open seats.
* ⏱️ **Idle Gap & Days Optimizer**: Filter by target days and sort by most compact schedules.
* 📄 **Direct Downloads**: Generate and download full **PDF reports** and **CSV spreadsheets** directly in your browser.
* 🌓 **Dark & Light Mode**: Seamless theme toggle with persistent preferences.
