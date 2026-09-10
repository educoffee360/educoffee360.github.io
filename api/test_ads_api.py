from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import app

client = TestClient(app)

def test_ads_list_route_exists_for_authenticated_or_role():
    response = client.get('/api/ads')
    # unauthenticated route should not crash; it should return a 401/403 or a list
    assert response.status_code in (200, 401, 403)
