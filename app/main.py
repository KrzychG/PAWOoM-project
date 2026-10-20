from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict

class BikeSchema(BaseModel):
    id: str = Field(..., min_length=3, max_length=10, description="Unikalny identyfikator roweru, np. BIKE-01")
    model: str = Field(..., min_length=2, description="Model roweru, np. CityBike")
    status: str = Field("free", description="Status: free, rented, service")

class UpdateStatusSchema(BaseModel):
    status: str = Field(..., description="Nowy status roweru")

def create_app() -> FastAPI:
    app = FastAPI(title="Bike Rental Service", version="1.0.0")

    # Baza danych w pamięci procesu
    db_bikes: Dict[str, dict] = {
        "BIKE-01": {"id": "BIKE-01", "model": "Veturilo Standard", "status": "free"},
        "BIKE-02": {"id": "BIKE-02", "model": "Veturilo E-Bike", "status": "service"}
    }

    @app.get("/health", status_code=status.HTTP_200_OK)
    def health_check():
        return {"status": "ok", "service": "bike-rental-service"}

    @app.get("/bikes", response_model=List[BikeSchema])
    def get_all_bikes():
        return list(db_bikes.values())

    @app.get("/bikes/{bike_id}", response_model=BikeSchema)
    def get_bike_by_id(bike_id: str):
        if bike_id not in db_bikes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Rower o identyfikatorze {bike_id} nie istnieje."
            )
        return db_bikes[bike_id]

    @app.patch("/bikes/{bike_id}/status", response_model=BikeSchema)
    def update_bike_status(bike_id: str, payload: UpdateStatusSchema):
        if bike_id not in db_bikes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Nie znaleziono roweru o podanym ID."
            )
        
        current_bike = db_bikes[bike_id]
        new_status = payload.status
        allowed_statuses = ["free", "rented", "service"]

        if new_status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Nieprawidłowy status. Dozwolone to: {allowed_statuses}"
            )

        if current_bike["status"] == new_status:
            return current_bike

        # IMPLEMENTACJA REGUŁY BIZNESOWEJ (409 Conflict)
        if new_status == "rented" and current_bike["status"] == "service":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nie można wypożyczyć roweru, który aktualnie znajduje się w naprawie (status: service)."
            )
            
        if new_status == "rented" and current_bike["status"] == "rented":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rower jest już obecnie wypożyczony."
            )

        current_bike["status"] = new_status
        db_bikes[bike_id] = current_bike
        
        return current_bike

    return app

app = create_app()