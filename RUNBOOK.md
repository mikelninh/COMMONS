# v0.2 Runbook

## Install

```bash
git clone https://github.com/mikelninh/COMMONS.git
cd COMMONS
python -m venv .venv
```

Activate the environment.

macOS / Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Then install:

```bash
pip install -e ".[dev]"
```

## Configure Jev

The official `typesafe-sdk` reads `TYPESAFE_API_KEY` from the process environment.

Windows PowerShell:

```powershell
$env:TYPESAFE_API_KEY="your_typesafe_key_here"
```

macOS / Linux:

```bash
export TYPESAFE_API_KEY="your_typesafe_key_here"
```

Do **not** commit the real key. `.env` is gitignored and `.env.example` documents the variable name, but COMMONS does not currently auto-load `.env`.

## Run the Civic Intelligence Lab

```bash
uvicorn commons.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Try all three modes:

- citizen,
- public official,
- community.

The public `/analyse` endpoint is stateless. It does not write the submitted problem to the SQLite outcome store.

## Run one CLI case

```bash
commons "I received a government letter and cannot tell which deadline applies." --language en
```

## Run the live 32-case civic benchmark

```bash
python scripts/eval_civic.py
```

Use `--limit 5` for a cheap smoke test first.

The benchmark reports:

- domain accuracy,
- acceptable capability rate,
- acceptable route rate,
- human-review Brier proxy,
- automation-safety Brier proxy,
- false-safe rate,
- authority-violation rate,
- latency,
- estimated input cost when token usage is available,
- route performance by language.

Resolution, recurrence and agency are deliberately **not** fabricated from the synthetic set. Those require real outcome follow-up.

## Run the architecture simulation

No API key required:

```bash
python scripts/simulate_architecture.py
```

The simulation is for architecture stress testing only. Its assumptions are illustrative and are not Jev performance claims.

## Persistent outcome path

POST a case to `/cases`, then attach reality later to:

```text
/cases/{case_id}/outcome
```

Outcome records can include resolution status, verification, time, intelligence cost, user benefit, agency rating and recurrence.

## Deploy to Vercel

The repository includes a root `app.py` entrypoint that exposes the FastAPI app.

After importing the repository into Vercel, add this secret in:

```text
Project → Settings → Environment Variables
```

Key:

```text
TYPESAFE_API_KEY
```

Apply it to Preview and/or Production as appropriate, then redeploy.

Never expose the TypeSafe key in browser JavaScript or a public environment variable.

## Tests

```bash
pytest -q
```

Deterministic policy tests require no Jev key.
