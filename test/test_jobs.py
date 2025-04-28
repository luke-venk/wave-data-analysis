import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import pytest
import requests
import time
import logging
import jobs
from unittest.mock import patch


########## CONFIG ##########
BASE_URL = 'http://flask-app:5000'  # Base URL is based on Flask app container
_log_level = os.environ.get('LOG_LEVEL')
logging.basicConfig(level=_log_level)

########## INTEGRATION TESTS ##########

########## UNIT TESTS ##########

# TODO: @Tavishka
@patch('jobs.jdb')
@patch('jobs.q')
def test_add_job(mock_q, mock_jdb):
    """Test the add_job function."""
    job = jobs.add_job(9, 2018, "stats")
    assert isinstance(job, dict)
    assert 'id' in job
    assert job['status'] == 'Pending'
    assert job['month'] == 9
    assert job['year'] == 2018
    assert job['method'] == 'stats'
    mock_q.put.assert_called_once_with(job['id'])
    mock_jdb.set.assert_called_once()

@patch('jobs.jdb')
def test_get_job_by_id(mock_jdb):
    """Test the get_job_by_id function."""
    mock_jdb.get.return_value = b'{"id": "1234", "status": "Pending"}'
    job = jobs.get_job_by_id("1234")
    assert isinstance(job, dict)
    assert job['id'] == "1234"
    assert job['status'] == "Pending"
    mock_jdb.get.assert_called_once_with("1234")

@patch('jobs.jdb')
def test_update_job_status(mock_jdb):
    """Test the update_job_status function."""
    mock_jdb.get.return_value = b'{"id": "1234", "status": "Pending"}'
    result = jobs.update_job_status("1234", "Completed")
    assert result is None
    mock_jdb.get.assert_called_once_with("1234")
    mock_jdb.set.assert_called_once()

@patch('jobs.resdb')
def test_save_results(mock_resdb):
    """Test the save_results function."""
    mock_resdb.set.return_value = True
    result = jobs.save_results("1234", {"result": "data"})
    assert result is None
    mock_resdb.set.assert_called_once_with("1234", '{"result": "data"}')

@patch('jobs.resdb')
def test_get_results_by_id(mock_resdb):
    """Test the get_results_by_id function."""
    mock_resdb.get.return_value = b'{"result": "data"}'
    result = jobs.get_results_by_id("1234")
    assert isinstance(result, dict)
    assert result['result'] == "data"
    mock_resdb.get.assert_called_once_with("1234")


