from fastapi import FastAPI

from . import items, users


def register_routes(app: FastAPI) -> None:
    app.include_router(users.router)
    app.include_router(items.router)

