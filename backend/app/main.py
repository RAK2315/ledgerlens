"""FastAPI app: CORS, error shape, routes. Startup only prepares the database."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import db, settings
from .routes import api


settings.load_env_file()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    db.fail_stale_runs()
    yield


app = FastAPI(title="LedgerLens API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins(), allow_methods=["*"], allow_headers=["*"])
app.include_router(api.router)


@app.exception_handler(api.ApiError)
async def api_error(_: Request, error: api.ApiError) -> JSONResponse:
    return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": error.message}})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": str(error.errors()[0]["msg"])}})
