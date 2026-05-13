from fastapi import APIRouter

from app.api.routes import (
    events,
    expenses,
    login,
    notifications,
    settlements,
    users,
    utils,
)

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(events.router)
api_router.include_router(expenses.router)
api_router.include_router(settlements.router)
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
