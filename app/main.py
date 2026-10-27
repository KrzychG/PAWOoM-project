import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from typing import List

from app.database import Base, make_database
from app.cache import JsonCache
from app.repository import BikeRepository

class BikeSchema(BaseModel):
    id: str = Field(..., min_length=3, max_length=10)
    model: str = Field(..., min_length=2)
    status: str = Field("free")

    class Config:
        from_attributes = True

class UpdateStatusSchema(BaseModel):
    status: str = Field(...)

def create_app(database_url=None, redis_client=None):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./app.db")
        engine, sessions = make_database(db_url)
        
        Base.metadata.create_all(engine)
        
        repo = BikeRepository(sessions)
        repo.seed_initial_data()
        
        app.state.engine = engine
        app.state.repository = repo
        
        # Automatyczne wykrywanie hosta Redisa w sieci Docker Compose
        redis_host = os.getenv("REDIS_HOST", "redis")
        
        if redis_client is None:
            import redis
            actual_client = redis.Redis(
                host=redis_host,
                port=6379,
                decode_responses=True,
                socket_timeout=1.0
            )
        else:
            actual_client = redis_client
        
        prefix = os.getenv("CACHE_PREFIX", "lab2:album12345:bike-rental-service")
        ttl = int(os.getenv("CACHE_TTL_SECONDS", "60"))
        
        app.state.cache = JsonCache(actual_client, prefix=prefix, ttl=ttl, resource_name="bike")
        app.state.redis = actual_client
        
        yield
        engine.dispose()

    app = FastAPI(title="Bike Rental Service", version="2.0.0", lifespan=lifespan)

    @app.get("/health", status_code=status.HTTP_200_OK)
    def health_check():
        return {"status": "ok", "service": "bike-rental-service"}

    @app.get("/bikes", response_model=List[BikeSchema])
    def get_all_bikes(request: Request):
        return request.app.state.repository.get_all()

    @app.get("/bikes/{bike_id}", response_model=BikeSchema)
    def get_bike_by_id(bike_id: str, request: Request, response: Response):
        cache = request.app.state.cache
        repo = request.app.state.repository
        
        cached, source = cache.get(bike_id)
        if cached is not None:
            response.headers["X-Cache"] = source
            return cached
            
        result = repo.get(bike_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Nie znaleziono roweru o podanym ID.")
            
        payload = BikeSchema.model_validate(result).model_dump(mode="json")
        if source != "BYPASS":
            cache.put(bike_id, payload)
            
        response.headers["X-Cache"] = source
        return payload

    @app.patch("/bikes/{bike_id}/status", response_model=BikeSchema)
    def update_bike_status(bike_id: str, payload: UpdateStatusSchema, request: Request):
        repo = request.app.state.repository
        cache = request.app.state.cache
        
        allowed_statuses = ["free", "rented", "service"]
        if payload.status not in allowed_statuses:
            raise HTTPException(
                status_code=422,
                detail=f"Nieprawidłowy status. Dozwolone to: {allowed_statuses}"
            )
            
        try:
            updated = repo.update_status(bike_id, payload.status)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
            
        # Unieważnienie klucza po udanym zatwierdzeniu transakcji bazy danych
        cache.delete(bike_id)
        return BikeSchema.model_validate(updated)

    return app
