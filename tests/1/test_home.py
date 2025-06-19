import requests

def test_home__has_correct_contents(services, wipe_data):
    response = requests.get(f"{services['esrs']}/")
    assert response.status_code == 200  # fail early if broken
    assert response.text.startswith('<!doctype html><html lang="en"><head><title>Elasticsearch Relevance Studio</title>')