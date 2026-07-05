"""Plugin introspection endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import CurrentUser

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class PluginInfo(BaseModel):
    name: str
    version: str
    description: str
    distributions: list[str]
    exporters: list[str]
    knowledge_source: str | None


@router.get("", response_model=list[PluginInfo])
def list_plugins(_: CurrentUser):
    from app.plugins import registry

    return [
        PluginInfo(
            name=m.name,
            version=m.version,
            description=m.description,
            distributions=[d.type_name for d in m.distributions],
            exporters=[e.format_id for e in m.exporters],
            knowledge_source=m.knowledge.source if m.knowledge else None,
        )
        for m in registry.manifests
    ]
