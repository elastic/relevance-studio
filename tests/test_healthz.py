import requests
    
def test_api_healthz(services):
    r = requests.get(f"{services['esrs']}/healthz")
    assert r.status_code == 200
    assert r.json() == { "acknowledged": True }