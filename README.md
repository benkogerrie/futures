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
|   |-- tsconfig.json
|   `-- vercel.json
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

## Deploy naar Vercel (frontend)

De repository is een monorepo: de Next.js-app staat in `frontend/`. Vercel moet daarom die map als root gebruiken.

### Stap 1: Project aanmaken

1. Ga naar [vercel.com](https://vercel.com) en log in (bij voorkeur met hetzelfde GitHub-account als de repo).
2. **Add New…** → **Project** → importeer `benkogerrie/futures`.
3. Onder **Configure Project**:
   - **Root Directory**: klik **Edit**, kies **`frontend`**, bevestig.
   - **Framework Preset**: moet **Next.js** zijn (automatisch).
   - **Build Command**: laat staan op `npm run build` (of wat Vercel voorstelt; dit komt overeen met `frontend/vercel.json`).
   - **Output Directory**: niet handmatig invullen voor Next.js (Vercel regelt dit).

### Stap 2: Omgevingsvariabelen

1. In hetzelfde scherm, sectie **Environment Variables** (of later: **Project** → **Settings** → **Environment Variables**):
   - Voeg toe: `NEXT_PUBLIC_API_URL` = de publieke URL van je FastAPI-backend zodra die online staat (bijv. `https://api.jouwdomein.nl`), voor **Production** (en eventueel **Preview**).
   - Voor een eerste deploy zonder live API kun je tijdelijk `http://localhost:8000` zetten; dat werkt alleen in de browser vanaf je eigen machine, niet voor echte bezoekers. Zodra de API ergens host, vervang je deze waarde.

2. **Deploy** start de eerste build.

### Stap 3: Na de eerste deploy

1. **Project** → **Deployments**: open de laatste deployment; bij falen staan foutregels in de build-log.
2. **Settings** → **Domains**: koppel je eigen domein als je dat wilt.
3. Elke push naar `main` triggert doorgaans een nieuwe production deployment (standaard Git-integratie).

### Lokaal met de Vercel CLI (optioneel)

```powershell
cd frontend
npm i -g vercel
vercel login
vercel
```

Volg de prompts; kies hetzelfde team en link naar de bestaande GitHub-repo als dat wordt gevraagd. Zorg dat de **Root** op `frontend` staat (of run `vercel` vanuit `frontend/`).

### Bestanden in deze repo

- `frontend/vercel.json` — expliciet Next.js, EU-regio `fra1`, vaste `install`/`build` voor voorspelbare builds.
- `frontend/.env.example` — template voor `NEXT_PUBLIC_API_URL` (op Vercel zet je de echte waarden in het dashboard, niet in git).
