import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import pytest
import requests
import time
import logging
import worker
from unittest.mock import patch, MagicMock

########## CONFIG ##########
BASE_URL = 'http://flask-app:5000'
_log_level = os.environ.get('LOG_LEVEL')
logging.basicConfig(level=_log_level)

########## INTEGRATION TESTS ##########

########## UNIT TESTS ##########

# TODO: @Tavishka

@patch('worker.q')
@patch('worker.jdb')
def test_pull_job(mock_jdb, mock_q):
    """Test pull_job function to update job status."""

    def mock_consume(*args, **kwargs):
        yield "1234"

    mock_q.consume.side_effect = mock_consume
    mock_jdb.get.return_value = b'{"id": "1234", "status": "Pending"}'

    worker.pull_job("1234")

    mock_jdb.set.assert_called_once()

@patch('worker.rd')
def test_wave_statistics_empty(mock_rd):
    """Test wave_statistics where no keys are present."""
    mock_rd.keys.return_value = []
    stats = worker.wave_statistics(9, 2017)

    assert isinstance(stats, str)
    assert 'No wave data found' in stats or 'count' in stats

@patch('worker.rd')
def test_wave_statistics_with_data(mock_rd):
    """Test wave_statistics with fake data."""
    fake_data = [
        b'{"Date/Time": "09/12/2017 18:30", "Hs": 1.3, "Hmax": 2.0, "Tz": 5, "Tp": 9, "Peak Direction": 270, "SST": 25}',
        b'{"Date/Time": "09/12/2017 18:40", "Hs": 1.4, "Hmax": 2.2, "Tz": 6, "Tp": 10, "Peak Direction": 280, "SST": 26}'
    ]
    mock_rd.keys.return_value = ['wave:0', 'wave:1']
    mock_rd.get.side_effect = fake_data

    stats = worker.wave_statistics(9, 2017)

    assert isinstance(stats, str)
    assert "count" in stats

@patch('worker.rd')
def test_plot_height_vs_time_real_behavior(mock_rd):
    """Test plot_height_vs_time function returns a Matplotlib Figure or valid path."""
    fake_data = [
        b'{"Date/Time": "09/12/2017 18:30", "Hs": 1.3}',
        b'{"Date/Time": "09/12/2017 18:40", "Hs": 1.4}'
    ]
    mock_rd.keys.return_value = ['wave:0', 'wave:1']
    mock_rd.get.side_effect = fake_data

    fig_or_output = worker.plot_height_vs_time(9, 2017)

    try:
        import matplotlib.figure
        assert isinstance(fig_or_output, (matplotlib.figure.Figure, str))
    except ImportError:
        assert isinstance(fig_or_output, str)

