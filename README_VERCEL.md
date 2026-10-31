# Deploy Public Grievance AI on Vercel

## Important limitation
This FastAPI MVP uses SQLite and local attachment storage. Vercel Python Functions have ephemeral filesystem storage, so complaints and uploaded files stored under `/tmp` can disappear when the function is recycled or redeployed. **This deployment is suitable for a demo, not real citizen data.** For durable data, connect a hosted PostgreSQL database (for example Neon or Supabase) and object storage (for example Vercel Blob or Supabase Storage), then update the app to use them. Add authentication/authorization, secure upload validation, rate limits, and privacy controls before public use.

## Deploy from GitHub
1. Extract this ZIP.
2. Create a GitHub repository and upload the contents of this folder (including `vercel.json` and `api/index.py`) to its root.
3. Sign in at https://vercel.com and choose **Add New → Project**.
4. Import the repository.
5. Framework Preset: **Other**. Leave the build command blank; Vercel uses `vercel.json` and `@vercel/python`.
6. Click **Deploy**. Vercel will provide a public URL.
7. Open `https://YOUR-DEPLOYMENT.vercel.app/health` and confirm it returns `{"status":"ok",...}`.

## Local run (unchanged)
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```
Open http://127.0.0.1:8000.

## Included Vercel entry point
`api/index.py` imports the FastAPI `app` from the project root. `vercel.json` routes requests to this function. When `VERCEL` is set, SQLite and uploads are placed in `/tmp/public_grievance_ai` to avoid writing into the read-only deployment directory. `/tmp` is still ephemeral.
