import os
from fastapi import FastAPI
from routes import props, keys
from middleware.auth import APIKeyMiddleware

app = FastAPI(title="propedge-api", version="0.1.0")

app.add_middleware(APIKeyMiddleware)

app.include_router(props.router, prefix="/v1")
app.include_router(keys.router, prefix="/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
