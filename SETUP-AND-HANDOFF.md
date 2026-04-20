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
NEXT_PUBLIC_API_URL=https://futures-production-3c71.up.railway.app
```

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

`NEXT_PUBLIC_API_URL`:

```env
https://futures-production-3c71.up.railway.app
```

## 6) Snelle check na opstart

1. Open lokaal dashboard op `http://localhost:3000`.
2. Controleer dat de statusbalk groen is (live API).
3. Als fallback/oranje zichtbaar is:
   - controleer `frontend/.env`
   - herstart dev server
   - test `/health` URL in browser

## 7) Verder werken in Cursor

1. Open de map `futures` in Cursor.
2. Laat Cursor eerst `README.md` en dit bestand (`SETUP-AND-HANDOFF.md`) lezen.
3. Ga daarna door met de volgende sprint (chart-data via backend in plaats van mock).
