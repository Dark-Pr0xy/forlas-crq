"""Plugin manifest + global registry."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any

import numpy as np

logger = logging.getLogger("forlas.plugins")

ENTRY_POINT_GROUP = "forlas.plugins"


@dataclass(frozen=True)
class DistributionPlugin:
    """Add a custom distribution type usable in scenario inputs.

    `sampler(rng, n, params) -> np.ndarray` returns `n` samples; `params` is
    the per-input dict the scenario stored.
    """

    type_name: str
    sampler: Callable[[np.random.Generator, int, dict[str, Any]], np.ndarray]
    description: str = ""


@dataclass(frozen=True)
class ExporterPlugin:
    """Add an extra export format for simulations or portfolios.

    `render(context) -> (bytes, media_type, filename)`.
    """

    format_id: str
    label: str
    target: str  # "simulation" | "report" | "register"
    media_type: str
    render: Callable[[dict[str, Any]], tuple[bytes, str, str]]


@dataclass(frozen=True)
class KnowledgePlugin:
    """Seed additional threats/controls/benchmarks at startup.

    `entries` is a dict matching the catalogue shapes consumed by
    `app.knowledge.seed`.
    """

    source: str
    threats: list[dict[str, Any]] = field(default_factory=list)
    controls: list[dict[str, Any]] = field(default_factory=list)
    benchmarks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str = ""
    distributions: list[DistributionPlugin] = field(default_factory=list)
    exporters: list[ExporterPlugin] = field(default_factory=list)
    knowledge: KnowledgePlugin | None = None


@dataclass
class Registry:
    manifests: list[PluginManifest] = field(default_factory=list)
    distributions: dict[str, DistributionPlugin] = field(default_factory=dict)
    exporters: dict[str, ExporterPlugin] = field(default_factory=dict)
    knowledge: list[KnowledgePlugin] = field(default_factory=list)
    discovered: bool = False

    def register(self, manifest: PluginManifest) -> None:
        if any(m.name == manifest.name for m in self.manifests):
            logger.warning("Plugin '%s' already registered — skipping duplicate", manifest.name)
            return
        self.manifests.append(manifest)
        for d in manifest.distributions:
            if d.type_name in self.distributions:
                logger.warning(
                    "Plugin '%s' distribution '%s' collides — keeping first.",
                    manifest.name,
                    d.type_name,
                )
                continue
            self.distributions[d.type_name] = d
        for e in manifest.exporters:
            if e.format_id in self.exporters:
                logger.warning(
                    "Plugin '%s' exporter '%s' collides — keeping first.",
                    manifest.name,
                    e.format_id,
                )
                continue
            self.exporters[e.format_id] = e
        if manifest.knowledge:
            self.knowledge.append(manifest.knowledge)
        logger.info(
            "Loaded plugin '%s' v%s — %d distributions, %d exporters, knowledge=%s",
            manifest.name,
            manifest.version,
            len(manifest.distributions),
            len(manifest.exporters),
            bool(manifest.knowledge),
        )


registry = Registry()


def discover(force: bool = False) -> Registry:
    """Walk the configured entry-point group and register every manifest."""
    if registry.discovered and not force:
        return registry
    eps = entry_points()
    group = (
        eps.select(group=ENTRY_POINT_GROUP)
        if hasattr(eps, "select")
        else eps.get(ENTRY_POINT_GROUP, [])
    )
    for ep in group:
        try:
            manifest = ep.load()
        except Exception:
            logger.exception("Failed to load plugin entry point %s", ep.name)
            continue
        if not isinstance(manifest, PluginManifest):
            logger.warning(
                "Entry point %s did not provide a PluginManifest (got %r) — skipping.",
                ep.name,
                type(manifest),
            )
            continue
        registry.register(manifest)
    registry.discovered = True
    return registry
