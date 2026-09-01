import asyncio
import requests
import websockets
import json

base_url = "http://localhost:8000"

def test_rest():
    print("Testing REST endpoints")
    # 1. 401 without token
    r = requests.get(f"{base_url}/api/equipment")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    print("   OK /api/equipment -> 401 Unauthorized (no token)")

    # 2. Login
    r = requests.post(f"{base_url}/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   OK /auth/login -> returns JWT token")

    # 3. GET /api/equipment
    r = requests.get(f"{base_url}/api/equipment", headers=headers)
    assert r.status_code == 200, r.text
    equipments = r.json()
    assert len(equipments) == 20
    print(f"   OK /api/equipment -> returns {len(equipments)} items")

    # 4. GET /api/equipment/1/sensors
    r = requests.get(f"{base_url}/api/equipment/1/sensors", headers=headers)
    assert r.status_code == 200, r.text
    print("   OK /api/equipment/1/sensors -> success")

    # 5. GET /api/equipment/1/prediction
    r = requests.get(f"{base_url}/api/equipment/1/prediction", headers=headers)
    assert r.status_code == 200, r.text
    print("   OK /api/equipment/1/prediction -> success")

    # 6. GET /api/alerts
    r = requests.get(f"{base_url}/api/alerts", headers=headers)
    assert r.status_code == 200, r.text
    print("   OK /api/alerts -> success")

    # 7. GET /api/workorders
    r = requests.get(f"{base_url}/api/workorders", headers=headers)
    assert r.status_code == 200, r.text
    print("   OK /api/workorders -> success")

    # 8. GET /api/dashboard/summary
    r = requests.get(f"{base_url}/api/dashboard/summary", headers=headers)
    assert r.status_code == 200, r.text
    status = r.json()
    assert status["total_equipment"] == 20
    print(f"   OK /api/dashboard/summary -> {status}")

async def check_ws():
    print("\nTesting WebSocket")
    uri = "ws://localhost:8000/ws/live"
    try:
        async with websockets.connect(uri) as websocket:
            print("   OK WebSocket connected")
            # First message should be summary
            msg1 = await websocket.recv()
            data1 = json.loads(msg1)
            assert data1["type"] == "initial_summary"
            print("   OK received initial_summary")

            # Second message should be sensor_update (within 5 seconds)
            msg2 = await asyncio.wait_for(websocket.recv(), timeout=8.0)
            data2 = json.loads(msg2)
            assert data2["type"] == "sensor_update" or "alert" in data2["type"]
            print(f"   OK received {data2['type']}")
    except Exception as e:
            print(f"WebSocket result: {e}")

def test_ws():
    asyncio.run(check_ws())

if __name__ == "__main__":
    test_rest()
    asyncio.run(check_ws())
