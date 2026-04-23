# Setup op een andere PC (Cursor handoff)

Gebruik dit document als startpunt wanneer je op een nieuwe machine verder werkt aan deze repo.

## 1) Repository clonen

```powershell
git clone https://github.com/benkogerrie/futures.git
cd futures
```

## 2) Frontend lokaal opstarten

```powershell
cd frontend
copy .env.example .env
```

Zet in `frontend/.env`:

```env
DASHBOARD_API_URL=https://futures-production-3c71.up.railway.app
NEXT_PUBLIC_API_URL=https://futures-production-3c71.up.railway.app
```

`DASHBOARD_API_URL` is **server-only** (geen rebuild op Vercel na wijziging). `NEXT_PUBLIC_*` blijft bruikbaar voor lokaal/compat.

Installeer en start:

```powershell
npm.cmd install
npm.cmd run dev
```

Open daarna `http://localhost:3000`.

## 3) Windows npm/PowerShell issue (indien van toepassing)

Als `npm` faalt met `running scripts is disabled`, gebruik:

```powershell
npm.cmd install
npm.cmd run dev
```

Optioneel (permanente fix voor je user):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## 4) Huidige productie URLs

- Frontend (Vercel): `https://futures-theta.vercel.app`
- Backend API (Railway): `https://futures-production-3c71.up.railway.app`
- Health endpoint: `https://futures-production-3c71.up.railway.app/health`

## 5) Railway en Vercel env waarden

### Railway

`FRONTEND_ORIGIN`:

```env
https://futures-theta.vercel.app,http://localhost:3000
```

### Vercel

1. **DASHBOARD_API_URL** (aanbevolen) — zelfde Railway-URL; dashboard haalt data per request server-side op.

```env
DASHBOARD_API_URL=https://futures-production-3c71.up.railway.app
```

2. **NEXT_PUBLIC_API_URL** (optioneel) — zelfde URL; alleen nodig als je de URL ook in de browserbundle wilt; na wijziging altijd **Redeploy**.

```env
NEXT_PUBLIC_API_URL=https://futures-production-3c71.up.railway.app
```

## 6) Snelle check na opstart

1. Open lokaal dashboard op `http://localhost:3000`.
2. Controleer dat de statusbalk groen is (live API) en dat er een **tweede regel** met `Backend: … · … velden` staat (dan komt de data echt van Railway/Saxo).
3. Als fallback/oranje zichtbaar is:
   - op **Vercel**: `DASHBOARD_API_URL` gezet? (Project → Settings → Environment Variables → Production)
   - lokaal: `frontend/.env` en dev server herstart
   - test `https://…railway…/health` in de browser

## 7) Verder werken in Cursor

1. Open de map `futures` in Cursor.
2. Laat Cursor eerst `README.md` en dit bestand (`SETUP-AND-HANDOFF.md`) lezen.
3. Ga daarna door met de volgende sprint (chart-data via backend in plaats van mock).
