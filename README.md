# Quant Trading Dashboard

NDQ trading dashboard met Next.js frontend en FastAPI backend. Sprint 2 bevat live account-koppeling met Saxo OpenAPI, backend-enforced trading rules en tradingagents-integratie.

## Handoff / Nieuwe PC

Voor opstart op een andere machine, volg: `SETUP-AND-HANDOFF.md`.

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

## Deploy naar Railway (backend)

Voor deze repo is Railway ingesteld om de backend vanuit `backend/` te draaien.

### Stap 1: Nieuw Railway project

1. Ga naar [railway.app](https://railway.app) en log in met GitHub.
2. Klik **New Project** → **Deploy from GitHub repo**.
3. Kies repo `benkogerrie/futures`.
4. Open de service-instellingen en zet de **Root Directory** op `backend`.

### Stap 2: Runtime en start

- Railway gebruikt `requirements.txt` voor dependencies.
- `Procfile` start de API met:
  - `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- `runtime.txt` pinnt Python op `3.13.5`.

### Stap 3: Environment variables

Zet in Railway bij **Variables** minimaal:

- `FRONTEND_ORIGIN` = je Vercel URL(s), komma-gescheiden, bijvoorbeeld:
  - `https://your-app.vercel.app,https://your-domain.com,http://localhost:3000`

Voor Sprint 2 vul je ook:
- `SAXO_OPENAPI_BASE_URL`
- `SAXO_ACCESS_TOKEN`
- `SAXO_BALANCES_PATH` (default: `/port/v1/balances`)
- `SAXO_POSITIONS_PATH` (default: `/port/v1/positions`)
- `SAXO_TIMEOUT_SECONDS`
- `BOND_COLLATERAL_LTV90`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

### Nieuwe backend endpoints (Sprint 2)

- `GET /api/dashboard`  
  Haalt live account-overview op via Saxo OpenAPI:
  - cash balance
  - open options value
  - total margin available
  - total account value
- `POST /api/rules/check-trade`  
  Dwingt backend-risicoregels af:
  - obligaties zijn niet tradebaar (collateral-only)
  - hard limit: max 50 contracten

### Stap 4: Verifiëren

1. Wacht tot deployment groen is.
2. Open de gegenereerde Railway URL.
3. Controleer health endpoint:
   - `https://<jouw-railway-domein>/health`
4. Verwachte response:
   - `{"status":"ok"}`

### Stap 5: Koppelen met Vercel frontend

1. Ga in Vercel naar **Project Settings** → **Environment Variables**.
2. Zet:
   - `NEXT_PUBLIC_API_URL=https://<jouw-railway-domein>`
3. Redeploy de frontend op Vercel.

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
