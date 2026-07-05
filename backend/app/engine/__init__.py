"""Monte Carlo simulation engine — vectorised NumPy port of the Alpha.

Public entry point: `runSimulation(scenario, opts)` returns a `RunResult`
dataclass with the full payload the API serialises.
"""

from app.engine.simulation import ENGINE_VERSION, RunResult, run_simulation

__all__ = ["ENGINE_VERSION", "RunResult", "run_simulation"]
