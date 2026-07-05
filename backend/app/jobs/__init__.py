"""In-process background job runner.

Phase 2 will implement a small thread-pool based worker for long simulations
so the FastAPI request loop stays responsive. No Redis, no Celery — spec
explicitly forbids them.
"""
