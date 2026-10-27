from sqlalchemy import Column, String
from app.database import Base

class BikeRow(Base):
    __tablename__ = "bikes"
    
    id = Column(String(32), primary_key=True, index=True)
    model = Column(String(100), nullable=False)
    status = Column(String(20), default="free", nullable=False)
