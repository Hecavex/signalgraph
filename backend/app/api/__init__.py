from fastapi import APIRouter

from app.api import auth, dashboard, entities, export, graph, investigations, operations, reports

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(entities.router)
api_router.include_router(graph.router)
api_router.include_router(investigations.router)
api_router.include_router(reports.router)
api_router.include_router(operations.router)
api_router.include_router(export.router)
