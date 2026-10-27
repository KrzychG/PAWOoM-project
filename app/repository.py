from sqlalchemy.orm import sessionmaker
from app.db_models import BikeRow

class BikeRepository:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def get_all(self):
        with self.session_factory() as session:
            rows = session.query(BikeRow).all()
            return [{"id": r.id, "model": r.model, "status": r.status} for r in rows]

    def get(self, bike_id: str):
        with self.session_factory() as session:
            row = session.query(BikeRow).filter(BikeRow.id == bike_id).first()
            if row:
                return {"id": row.id, "model": row.model, "status": row.status}
            return None

    def update_status(self, bike_id: str, new_status: str):
        with self.session_factory() as session:
            with session.begin(): 
                row = session.query(BikeRow).filter(BikeRow.id == bike_id).first()
                if not row:
                    raise LookupError(f"Rower {bike_id} nie istnieje.")
                if new_status == "rented" and row.status == "service":
                    raise ValueError("Nie można wypożyczyć roweru, który aktualnie znajduje się w naprawie (status: service).")
                if new_status == "rented" and row.status == "rented":
                    raise ValueError("Rower jest już obecnie wypożyczony.")
                    
                row.status = new_status
                return {"id": row.id, "model": row.model, "status": row.status}

    def seed_initial_data(self):
        with self.session_factory() as session:
            with session.begin():
                if not session.query(BikeRow).filter(BikeRow.id == "BIKE-01").first():
                    session.add(BikeRow(id="BIKE-01", model="Veturilo Standard", status="free"))
                if not session.query(BikeRow).filter(BikeRow.id == "BIKE-02").first():
                    session.add(BikeRow(id="BIKE-02", model="Veturilo E-Bike", status="service"))
