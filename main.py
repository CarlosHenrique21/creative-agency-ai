from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.rag_routes import router as rag_router
from core.config import settings
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

app = FastAPI(
    title="Social Media Agency",
    description="Multi-agent system for social media flyer generation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(rag_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=settings.debug)
