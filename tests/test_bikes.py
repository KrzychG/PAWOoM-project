import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

# TEST 1: Zapis i Odczyt
def test_rent_bike_success(client):
    response = client.patch("/bikes/BIKE-01/status", json={"status": "rented"})
    assert response.status_code == 200
    assert response.json()["status"] == "rented"

    get_response = client.get("/bikes/BIKE-01")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "rented"

# TEST 2: Złe dane (422 Unprocessable Entity) - brak modyfikacji stanu
def test_invalid_status_value(client):
    response = client.patch("/bikes/BIKE-01/status", json={"status": "destroyed"})
    assert response.status_code == 422
    
    get_response = client.get("/bikes/BIKE-01")
    assert get_response.json()["status"] == "free"

# TEST 3: Reguła biznesowa / Konflikt (409 Conflict) - brak modyfikacji stanu
def test_rent_bike_in_service_should_fail(client):
    response = client.patch("/bikes/BIKE-02/status", json={"status": "rented"})
    
    assert response.status_code == 409
    assert "w naprawie" in response.json()["detail"]

    get_response = client.get("/bikes/BIKE-02")
    assert get_response.json()["status"] == "service"