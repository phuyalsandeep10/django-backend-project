from typing import Union

from fastapi import FastAPI
from src.config.settings import settings
from fastapi.middleware.cors import CORSMiddleware
from src.modules.auth.router import router as auth_router
from src.modules.organizations.router import router as organization_router

app = FastAPI()


app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description=settings.PROJECT_DESCRIPTION,
    )

    # CORS middleware
app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        
    )
# ...existing code...
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(organization_router,prefix='/organizations',tags=['organizations'])
# ...existing code...

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def read_items():
    return "Health check OK"


