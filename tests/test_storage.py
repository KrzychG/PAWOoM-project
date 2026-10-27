import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.cache import MemoryRedis

@pytest.fixture
def setup_env(tmp_path):
    db_url = f"sqlite:///{ (tmp_path / 'test_bike.db').as_posix() }"
    fake_redis = MemoryRedis()
    return db_url, fake_redis

#1: Weryfikacja Trwałości po Restarcie Instancji Aplikacji
def test_persistence_across_app_restarts(setup_env):
    db_url, fake_redis = setup_env
    
    app1 = create_app(database_url=db_url, redis_client=fake_redis)
    with TestClient(app1) as client1:
        response = client1.patch("/bikes/BIKE-01/status", json={"status": "rented"})
        assert response.status_code == 200

    # Start nowej instancji aplikacji
    app2 = create_app(database_url=db_url, redis_client=MemoryRedis())
    with TestClient(app2) as client2:
        response = client2.get("/bikes/BIKE-01")
        assert response.status_code == 200
        assert response.json()["status"] == "rented" 

#2: Scenariusz MISS -> HIT
def test_cache_aside_miss_then_hit(setup_env):
    db_url, fake_redis = setup_env
    app = create_app(database_url=db_url, redis_client=fake_redis)
    
    with TestClient(app) as client:
        # Pierwszy odczyt 
        r1 = client.get("/bikes/BIKE-01")
        assert r1.headers.get("X-Cache") == "MISS"
        
        # Drugi odczyt
        r2 = client.get("/bikes/BIKE-01")
        assert r2.headers.get("X-Cache") == "HIT"

#3 Unieważnianie pamięci podręcznej po modyfikacji danych
def test_cache_invalidation_after_update(setup_env):
    db_url, fake_redis = setup_env
    app = create_app(database_url=db_url, redis_client=fake_redis)
    
    with TestClient(app) as client:
        client.get("/bikes/BIKE-01")
        client.get("/bikes/BIKE-01")
        
        # Zmiana stanu roweru
        patch_res = client.patch("/bikes/BIKE-01/status", json={"status": "rented"})
        assert patch_res.status_code == 200
        
        r3 = client.get("/bikes/BIKE-01")
        assert r3.headers.get("X-Cache") == "MISS"
        assert r3.json()["status"] == "rented"

# 4 Obsługa awarii Cache odporność na brak Redis
def test_cache_failure_handling_bypass(setup_env):
    db_url, fake_redis = setup_env
    app = create_app(database_url=db_url, redis_client=fake_redis)
    
    with TestClient(app) as client:
        fake_redis.down = True  # Symulacja nagłej awarii
        
        # System nie może się wyłożyć
        response = client.get("/bikes/BIKE-01")
        assert response.status_code == 200
        assert response.headers.get("X-Cache") == "BYPASS"
        
        # Zapis do bazy danych musi się powieść
        patch_res = client.patch("/bikes/BIKE-01/status", json={"status": "rented"})
        assert patch_res.status_code == 200
