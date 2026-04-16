# Quant Trading Dashboard

Sprint 1 skeleton for a dark-mode NDQ trading dashboard with a Next.js frontend and FastAPI backend.

## Folder Structure

```text
.
|-- backend
|   |-- app
|   |   `-- main.py
|   `-- requirements.txt
|-- frontend
|   |-- app
|   |   |-- globals.css
|   |   |-- layout.tsx
|   |   `-- page.tsx
|   |-- components
|   |   |-- metric-card.tsx
|   |   |-- price-chart.tsx
|   |   |-- risk-monitor.tsx
|   |   `-- top-bar.tsx
|   |-- lib
|   |   `-- mock-data.ts
|   |-- next.config.ts
|   |-- next-env.d.ts
|   |-- package.json
|   |-- postcss.config.js
|   |-- tailwind.config.ts
|   `-- tsconfig.json
`-- README.md
```

## Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Frontend runs on `http://localhost:3000`.

## Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend runs on `http://localhost:8000`.
