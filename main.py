from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from enrichment import init_reasoning_cache
from middleware.auth import APIKeyMiddleware, init_keys_db
from routes import props, keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_keys_db()
    init_reasoning_cache()
    yield


app = FastAPI(title="propedge-api", version="0.1.0", lifespan=lifespan)

app.add_middleware(APIKeyMiddleware)

app.include_router(props.router, prefix="/v1")
app.include_router(keys.router, prefix="/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
