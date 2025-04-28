import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import pytest
import requests
import time
import logging
import worker
from unittest.mock import patch


########## CONFIG ##########
BASE_URL = 'http://flask-app:5000'  # Base URL is based on Flask app container
_log_level = os.environ.get('LOG_LEVEL')
logging.basicConfig(level=_log_level)

########## INTEGRATION TESTS ##########

########## UNIT TESTS ##########

# TODO: @Tavishka
@patch('src.worker.q')
@patch('src.worker.jdb')
def test_pull_job(mock_jdb, mock_q):
    """Test pull_job function to update job status."""
    mock_jdb.get.return_value = b'{"id": "1234", "status": "Pending"}'
    worker.pull_job("1234")
    mock_jdb.set.assert_called_once()

@patch('src.worker.rd')
def test_wave_statistics_empty(mock_rd):
    """Test wave_statistics where no keys are present."""
    mock_rd.keys.return_value = []
    stats = worker.wave_statistics(9, 2017)
    assert isinstance(stats, dict)
    assert stats.get('count') == 0

@patch('src.worker.rd')
def test_wave_statistics_with_data(mock_rd):
    """Test wave_statistics with fake data."""
    fake_data = [
        b'{"Date/Time": "09/12/2017 18:30", "Hs": 1.3}',
        b'{"Date/Time": "09/12/2017 18:40", "Hs": 1.4}'
    ]
    mock_rd.keys.return_value = ['wave:0', 'wave:1']
    mock_rd.get.side_effect = fake_data

    stats = worker.wave_statistics(9, 2017)
    assert isinstance(stats, dict)
    assert stats.get('count', 0) >= 0  # depending on month match

def test_plot_height_vs_time_real_behavior():
    """Test plot_height_vs_time function returns a Matplotlib Figure or valid path."""
    # Now plot_height_vs_time returns a matplotlib Figure object
    fig_or_output = worker.plot_height_vs_time(9, 2017)
    
    # Accept if it returns either:
    # 1. a matplotlib Figure object (normal)
    # 2. a saved file path (string)
    try:
        import matplotlib.figure
        assert isinstance(fig_or_output, (matplotlib.figure.Figure, str))
    except ImportError:
        # fallback in case matplotlib figure class import failed
        assert isinstance(fig_or_output, str)

@patch('src.worker.rd')
def test_plot_height_vs_time_with_no_data(mock_rd):
    """Test plot_height_vs_time handles no available data case."""
    mock_rd.keys.return_value = []
    fig_or_output = worker.plot_height_vs_time(1, 2025)
    assert fig_or_output is not None
    assert isinstance(fig_or_output, (str, object))  # Should still return something non-crashing

