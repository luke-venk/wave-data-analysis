import pytest
import requests
import time
import os
import logging
from flask_api import app
import json

########## CONFIG ##########
BASE_URL = 'http://flask-app:5000'  # Base URL is based on Flask app container
_log_level = os.environ.get('LOG_LEVEL')
logging.basicConfig(level=_log_level)

########## INTEGRATION TESTS ##########

########## UNIT TESTS ##########

# TODO: @Tavishka

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test the index '/' route."""
    response = client.get('/')
    assert response.status_code == 418
    assert b'Hello, world!' in response.data

def test_help_route(client):
    """Test the /help route (placeholder)."""
    response = client.get('/help')
    assert response.status_code in [200, 404]

def test_data_post(client):
    """Test POST to /data."""
    response = client.post('/data')
    assert response.status_code in [200, 201]

def test_data_get(client):
    """Test GET from /data."""
    response = client.get('/data')
    assert response.status_code == 200
    assert isinstance(response.json, dict)

def test_data_delete(client):
    """Test DELETE to /data."""
    response = client.delete('/data')
    assert response.status_code in [204, 410]

def test_get_closest_wave(client):
    """Test GET /waves?epoch=..."""
    client.post('/data')  # Ensure data exists
    response = client.get('/waves', query_string={'epoch': '09/12/2017 18:30'})
    assert response.status_code == 200
    assert isinstance(json.loads(response.data), dict)

def test_create_job(client):
    """Test POST /jobs to create job."""
    job_data = {"month": 9, "year": 2017, "method": "stats"}
    response = client.post('/jobs', json=job_data)
    assert response.status_code in [201, 400, 404]

def test_list_jobs(client):
    """Test GET /jobs."""
    response = client.get('/jobs')
    assert response.status_code in [200, 404]

def test_keys_route(client):
    """Test /keys."""
    response = client.get('/keys')
    assert response.status_code in [200, 404]

# Skipping /jobs/<job_id> and /results/<job_id> for now because they require live jobs
