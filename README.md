# Repox 🚀

> AI-Powered codebase tour guides and visual diagrams for non-technical founders, product managers, and developers.

Repox analyzes any software repository, maps out its architecture, parses file logic, and generates a personalized walk-through report complete with dynamic flowcharts, ERDs, sequence diagrams, and dependency trees—all tailored to your chosen technical audience level.

---

## 🎨 Key Features

- **Personalized Explanations**: Select your level (Beginner, Product, or Developer) to adjust language, technical depth, and jargon definitions.
- **Dynamic Mermaid Visualizations**: Automatically generates valid, renderable flowcharts for System Architecture, User Flow sequence maps, and Repository Folder hierarchies.
- **Security Pass**: Auto-scans and redacts leaked API keys or credentials before generating the final report.
- **Interactive Results Hub**: Access full explanations directly in the frontend dashboard or download the packaged ZIP output with an auto-indexed README.
- **Async Processing Pipeline**: Real-time progress updates and status polling to visualize analysis steps as they run.

---

## 🏗️ Project Architecture

```
Repox/
├── backend/          FastAPI Engine (Python 3.11)
│   ├── app/
│   │   ├── routes/    FastAPI routers (Upload, Status, Download, Results)
│   │   └── services/  Pipelines (Tech Detect, Relations, Diagrams, Validator, Packager)
│   └── storage/       Local SQLite DB & ephemeral analysis packages
└── frontend/         Next.js App Router (TypeScript + Tailwind CSS + shadcn/ui)
    └── app/           Dashboard, Upload, Live progress step list, Results hub
```

For a detailed view of the integration borders, check out the generated `system_architecture.mmd` inside the Results visualizer tab.

---

## 🔧 Installation & Local Setup

### 1. Backend Setup

Make sure you have **Python 3.11+** installed.

```bash
# Navigate to backend directory
cd backend

# Create & activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development server
uvicorn app.main:app --reload
```
*Creates the SQLite database and binds on [http://localhost:8000](http://localhost:8000).*

### 2. Frontend Setup

Make sure you have **Node.js 18+** installed.

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
*Serves the user dashboard on [http://localhost:3000](http://localhost:3000).*

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)
Create a `.env` file under `backend/` containing:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
STORAGE_DIR=storage
```
*Note: A Groq API key is required to utilize `llama-3.3-70b-versatile` for generating explanations. Create one in the [Groq Console](https://console.groq.com/keys).*

### Frontend (`frontend/.env.local`)
Create a `.env.local` file under `frontend/` containing:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## ⚠️ Known Limitations

1. **Static Analysis**: The engine parses dependencies and routes using regex pattern heuristics rather than AST parsing. It is fast and lightweight, but dynamic imports might be missed.
2. **Ephemeral storage**: On serverless environments (like Render's free tier), project outputs stored under `storage/projects/` will be wiped clean whenever the container sleeps or restarts.
3. **Groq Free-Tier Limits**: Pipeline steps process concurrently but stay under free-tier limits (~30 RPM). Large repositories are throttled slightly to prevent API rate limits.
