# Job Search Frontend

This Next.js app provides the web interface for the job-search API.

## Run locally

Start the FastAPI backend from `BE/`, then from the repository root open another terminal and run:

```powershell
cd FE
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). By default, requests under `/api` are proxied to `http://127.0.0.1:8000`. Set `API_URL` to use a different backend address.

## Checks

```powershell
npm run lint
npm test
npm run build
```
