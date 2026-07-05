from contextlib import asynccontextmanager
from app.database import db
from fastapi import FastAPI
from app.config import settings
from loguru import logger
from app.routers import documents

@asynccontextmanager
async def workingtime(app:FastAPI):
            logger.info("server for docflow starts")
            db.connect()

            yield

            logger.info("Server has been closed")
            db.disconnect()


app=FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=workingtime)#this will automatically run as it is decorated with @asynccontextmanager
#here fastapi khud documentation bhi bnadeti hai turant
app.include_router(documents.router)
#HealthCheck endpoint
@app.get("/health")
async def health_check():
    return{
        "status":"running",
        "app":settings.APP_NAME,
        "version": settings.APP_VERSION
    }