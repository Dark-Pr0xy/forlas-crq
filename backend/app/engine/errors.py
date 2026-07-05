"""Engine error types.

`SimulationInputError` is raised for anything the caller can fix by editing
the scenario inputs (missing variable, impossible bounds, unknown distribution).
The API layer maps it to HTTP 422 rather than 500.
"""

from __future__ import annotations


class SimulationInputError(ValueError):
    """A scenario's inputs are invalid or incomplete for the chosen mode."""


# Required input variables per decomposition mode.
REQUIRED_INPUTS: dict[str, tuple[str, ...]] = {
    "lef": ("lef", "plm", "slp_prob", "slm"),
    "tef-vuln": ("tef", "vuln", "plm", "slp_prob", "slm"),
    "full": ("tef", "tcap", "rs", "plm", "slp_prob", "slm"),
}


def validate_inputs(mode: str, inputs: dict) -> None:
    """Raise SimulationInputError if a required variable is missing/empty."""
    # Accept either the raw string or a DecompositionMode enum member.
    mode = getattr(mode, "value", mode)
    required = REQUIRED_INPUTS.get(mode)
    if required is None:
        raise SimulationInputError(
            f"Unknown decomposition mode {mode!r}. "
            f"Expected one of: {', '.join(REQUIRED_INPUTS)}."
        )
    if not isinstance(inputs, dict):
        raise SimulationInputError("Scenario inputs must be an object of distributions.")
    missing = [k for k in required if not inputs.get(k)]
    if missing:
        raise SimulationInputError(
            f"Mode '{mode}' requires input variable(s): {', '.join(missing)}."
        )
