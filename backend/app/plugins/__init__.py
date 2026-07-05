"""Plugin host.

Plugins register themselves via Python entry points under the
`forlas.plugins` group:

    [project.entry-points."forlas.plugins"]
    my_plugin = "my_pkg.forlas_plugin:plugin"

Where the referenced object is a `PluginManifest` instance. The host
collects every discovered manifest at startup and routes registrations to the
right subsystem:

    - distributions  → app.engine.distributions.sample dispatches to user
                       samplers by type name.
    - exporters      → reporting API exposes them as additional download formats.
    - knowledge      → catalogues seeded into the DB on first observation.
"""

from app.plugins.registry import (
    DistributionPlugin,
    ExporterPlugin,
    KnowledgePlugin,
    PluginManifest,
    discover,
    registry,
)

__all__ = [
    "DistributionPlugin",
    "ExporterPlugin",
    "KnowledgePlugin",
    "PluginManifest",
    "discover",
    "registry",
]
