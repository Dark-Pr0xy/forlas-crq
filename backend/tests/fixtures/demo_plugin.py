"""Demo plugin used by tests and as a copy-able template for real plugins.

Exposes one of each extension point:

    - a `weibull` distribution (NumPy scipy convenience)
    - an `xlsx-summary` exporter stub (returns a tiny CSV blob with media type)
    - a knowledge source contributing one threat
"""

from __future__ import annotations

import numpy as np

from app.plugins import (
    DistributionPlugin,
    ExporterPlugin,
    KnowledgePlugin,
    PluginManifest,
)


def _weibull(rng: np.random.Generator, n: int, params: dict) -> np.ndarray:
    shape = float(params.get("shape", 1.5))
    scale = float(params.get("max", 1.0))
    return scale * rng.weibull(shape, n)


def _xlsx_stub(context: dict) -> tuple[bytes, str, str]:
    # Real implementation would use openpyxl; this is just to demonstrate the
    # exporter contract for tests.
    payload = b"name,ale\n" + b"\n".join(
        f"{s['name']},{s['ale']}".encode()
        for s in context.get("portfolio", {}).get("per_scenario", [])
    )
    return payload, "text/csv", "demo_export.csv"


plugin = PluginManifest(
    name="forlas-demo-plugin",
    version="0.1.0",
    description="Reference plugin demonstrating each extension point.",
    distributions=[
        DistributionPlugin(
            type_name="weibull",
            sampler=_weibull,
            description="Weibull distribution (shape, scale from `max`).",
        ),
    ],
    exporters=[
        ExporterPlugin(
            format_id="xlsx-summary",
            label="Summary CSV (demo)",
            target="register",
            media_type="text/csv",
            render=_xlsx_stub,
        ),
    ],
    knowledge=KnowledgePlugin(
        source="demo-plugin",
        threats=[
            {
                "public_id": "demo-plugin-threat",
                "name": "Plugin-contributed threat",
                "category": "Demo",
                "description": "Seeded at startup by the demo plugin.",
                "references": [],
            }
        ],
    ),
)
