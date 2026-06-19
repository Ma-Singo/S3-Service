from fastapi import APIRouter
from app.api.routers.v1 import upload, assets

api_router = APIRouter()

api_router.include_router(upload.router)
api_router.include_router(assets.router)
