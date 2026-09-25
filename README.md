# CareSathi

CareSathi is a local-first prototype for booking trusted, non-clinical hospital attendants in India. Families can post a care request, nearby attendants can accept it, and both sides can track the assignment.

## Run locally

```powershell
python server.py
```

Open [http://localhost:8000](http://localhost:8000).

The SQLite database (`caresathi.db`) is created automatically on first run. Demo accounts are also seeded:

- Family: `family@demo.in` / `demo123`
- Caretaker: `asha@demo.in` / `demo123`

## What is included

- Family and caretaker registration/login
- Local SQLite persistence with salted password hashing and expiring sessions
- Family dashboard for creating and tracking care requests
- Ranked local caretaker directory for families
- Caretaker job feed with matching city, shift, earnings, and requirements
- OTP-secured shift start with a live timer
- Family-requested early ending and minute-based final payout
- Accept, start, early-end, and complete assignment lifecycle
- CareSathi-initiated pre-shift release with a required reason and audit trail
- Role-specific navigation, responsive design, safety messaging, and demo data
- Persistent light and dark themes
- Mutual post-shift ratings for families and CareSathis
- Private multi-family live-watch links with active viewer presence and WhatsApp sharing
- Skill and credential badges with specialized matching scores
- Demo marketplace data for Ahmedabad, Delhi, and Lucknow
- JSON API served by the same Python process

## Important scope note

CareSathi attendants provide non-clinical companionship and bedside assistance only. They are not a replacement for nurses, doctors, emergency services, or hospital staff. A production deployment would additionally need identity/background verification, hospital partnerships, payment escrow, dispute handling, privacy controls, audit logging, and legal/compliance review.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Publish to GitHub

The local database and environment files are excluded by `.gitignore`.

```powershell
git add .
git commit -m "Build CareSathi marketplace"
git remote add origin https://github.com/YOUR_USERNAME/caresathi.git
git push -u origin main
```

If Git asks for an author identity, configure your own GitHub name and verified email first:

```powershell
git config user.name "YOUR_NAME"
git config user.email "YOUR_GITHUB_EMAIL"
```

## Deploy to Vercel

CareSathi uses SQLite automatically when run locally. Vercel Functions have an ephemeral filesystem, so production uses PostgreSQL through `DATABASE_URL`.

1. Push this repository to GitHub.
2. In Vercel, select **Add New → Project** and import the GitHub repository.
3. Keep the framework preset as **Other**. `vercel.json` already configures the Python API and SPA routes.
4. From the Vercel project, add a PostgreSQL integration such as Neon from **Storage / Marketplace**.
5. Confirm the integration provides a `DATABASE_URL` environment variable to Production, Preview, and Development.
6. Deploy the project.
7. Open `/api/health` on the deployed domain. A successful production setup returns:

```json
{"ok": true, "database": "postgres"}
```

The schema and demo data are created idempotently on the first API cold start. Never commit `.env`, `caresathi.db`, database credentials, or Vercel project metadata.

### Production checklist

Before using real patient information, replace the demo verification state with a real identity/background-check process, add password reset and email/phone verification, configure rate limiting, review privacy and retention policies, and complete security and legal review.
