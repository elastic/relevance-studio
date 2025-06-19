import requests
from tests import utils

TEST_PROJECT_A = {
    "name": "Test A",
    "index_pattern": "test-a",
    "params": [ "text" ],
    "rating_scale": {  "min": 0, "max": 4 }
}

TEST_PROJECT_B = {
    "name": "Test B",
    "index_pattern": "test-b",
    "params": [ "text", "filter" ],
    "rating_scale": {  "min": 1, "max": 3 }
}

def test_api_projects_browse__no_index(services, clean_data):
    r = requests.get(f"{services['esrs']}/api/projects")
    assert r.status_code == 200
    body = r.json()
    body.pop("took")
    assert body["hits"]["hits"] == []
    assert body["hits"]["total"]["value"] == 0
    assert body["timed_out"] == False

def test_api_projects_create(services, clean_data):
    
    # Create the doc
    r = requests.post(f"{services['esrs']}/api/projects", json=TEST_PROJECT_A)
    assert r.status_code == 201
    body = r.json()
    _id = body["_id"]
    assert utils.is_uuid(_id)
    assert body["_index"] == "esrs-projects"
    assert body["forced_refresh"] == True
    assert body["result"] == "created"
    
    # Verify that the doc was created correctly
    r = requests.get(f"{services['esrs']}/api/projects/{_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["_id"] == _id
    assert body["_index"] == "esrs-projects"
    assert body["_source"] == TEST_PROJECT_A
    assert body["found"] == True

def test_api_projects_update(services, clean_data):
    
    # Create the doc
    r = requests.post(f"{services['esrs']}/api/projects", json=TEST_PROJECT_A)
    _id = r.json()["_id"]
    
    # Verify that the doc was created correctly
    r = requests.get(f"{services['esrs']}/api/projects/{_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["_id"] == _id
    assert body["_index"] == "esrs-projects"
    assert body["_source"] == TEST_PROJECT_A
    assert body["found"] == True
    
    # Update the doc
    r = requests.put(f"{services['esrs']}/api/projects/{_id}", json=TEST_PROJECT_B)
    assert r.status_code == 200
    body = r.json()
    assert body["_id"] == _id
    assert body["_index"] == "esrs-projects"
    assert body["forced_refresh"] == True
    assert body["result"] == "updated"
    
    # Verify that the doc was updated correctly
    r = requests.get(f"{services['esrs']}/api/projects/{_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["_id"] == _id
    assert body["_index"] == "esrs-projects"
    assert body["_source"] == TEST_PROJECT_B
    assert body["found"] == True

def test_api_projects_delete(services, clean_data):
    
    # Create the doc
    r = requests.post(f"{services['esrs']}/api/projects", json=TEST_PROJECT_A)
    _id = r.json()["_id"]
    
    # Verify that the doc was created correctly
    r = requests.get(f"{services['esrs']}/api/projects/{_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["_id"] == _id
    assert body["_index"] == "esrs-projects"
    assert body["_source"] == TEST_PROJECT_A
    assert body["found"] == True
    
    # Delete the doc
    r = requests.delete(f"{services['esrs']}/api/projects/{_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] == 1
    
    # Verify that the doc was delete correctly
    r = requests.get(f"{services['esrs']}/api/projects/{_id}")
    assert r.status_code == 404
    body = r.json()
    assert body["_id"] == _id
    assert body["_index"] == "esrs-projects"
    assert body["found"] == False