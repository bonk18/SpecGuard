# Repository Notes

- The FastAPI application and Pydantic contracts live under `backend/app`.
- Install `requirements-dev.txt` and run backend tests with `.venv/bin/python -m pytest`.
- Import public contracts from `app.schemas`; keep internal schema imports absolute.
- Do not push directly to `main`.
- Do not rename existing API fields or `maintainance.py` without checking every usage.
- Keep safety recommendations advisory and human-approved by default.
- Update schema tests, `docs/examples`, and `docs/SCHEMA_ARCHITECTURE.md` together.
