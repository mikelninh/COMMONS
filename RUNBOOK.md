# v0.1 Runbook

## Install

```bash
git clone https://github.com/mikelninh/COMMONS.git
cd COMMONS
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Configure Jev

Create a local `.env` or export:

```bash
export TYPESAFE_API_KEY="..."
```

The official `typesafe-sdk` reads `TYPESAFE_API_KEY`.

## Run one case

```bash
commons "I was charged twice and I need to know what to do."
```

## Run API

```bash
uvicorn commons.app:app --reload
```

Then POST:

```json
{
  "text": "I was charged twice and I need to know what to do.",
  "language": "en"
}
```

to `/cases`.

After reality tells us what happened, attach an outcome to:

`/cases/{case_id}/outcome`

## Run tests

```bash
pytest -q
```

The deterministic policy tests do not require a Jev API key.
