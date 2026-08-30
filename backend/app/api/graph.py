from __future__ import annotations

from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_viewer
from app.models import Entity, Relationship, User
from app.schemas import GraphEdge, GraphNode, GraphResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{entity_id}", response_model=GraphResponse)
def entity_graph(
    entity_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    relationship_type: list[str] | None = Query(default=None),
    entity_type: list[str] | None = Query(default=None),
    _: User = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> GraphResponse:
    root = db.get(Entity, entity_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    visited = {entity_id}
    queue = deque([(entity_id, 0)])
    edges: dict[str, Relationship] = {}
    while queue and len(visited) < 500:
        current, level = queue.popleft()
        if level >= depth:
            continue
        query = select(Relationship).where(
            or_(Relationship.source_entity_id == current, Relationship.target_entity_id == current)
        )
        if relationship_type:
            query = query.where(Relationship.type.in_(relationship_type))
        for edge in db.scalars(query.limit(500)).all():
            neighbor = edge.target_entity_id if edge.source_entity_id == current else edge.source_entity_id
            neighbor_entity = db.get(Entity, neighbor)
            if neighbor_entity is None or (entity_type and neighbor_entity.type not in entity_type):
                continue
            edges[edge.id] = edge
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, level + 1))
    entities = db.scalars(select(Entity).where(Entity.id.in_(visited))).all()
    return GraphResponse(
        nodes=[
            GraphNode(
                id=item.id,
                label=item.display_name or item.value,
                type=item.type,
                risk_score=item.risk_score,
                classification=item.classification,
            )
            for item in entities
        ],
        edges=[
            GraphEdge(
                id=item.id,
                source=item.source_entity_id,
                target=item.target_entity_id,
                type=item.type,
                confidence=item.confidence,
            )
            for item in edges.values()
        ],
        depth=depth,
    )
