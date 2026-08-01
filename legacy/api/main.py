from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import legacy.api.routes as routes
from legacy.api.database import Base, engine
import legacy.api.models as models

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=["*"]
)

app.include_router(routes.router)
