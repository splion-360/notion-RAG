from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth_router, chat_router, notion_router

app = FastAPI(
    title=settings.name,
    description=settings.description,
    version=settings.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix=f"{settings.prefix}/auth", tags=["authentication"])
app.include_router(notion_router, prefix=f"{settings.prefix}/notion", tags=["notion"])
app.include_router(chat_router, prefix=f"{settings.prefix}/chat", tags=["chat"])


@app.get("/")
async def root():
    return {"message": f"Backend is initialized and running\n version: {settings.version}"}
