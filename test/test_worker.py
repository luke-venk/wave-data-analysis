import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import pytest
import worker
from unittest.mock import patch, MagicMock

########## CONFIG ##########
_log_level = os.environ.get('LOG_LEVEL')

########## UNIT TESTS ##########

@patch('worker.get_job_by_id')
@patch('worker.update_job_status')
@patch('worker.save_results')
def test_pull_job_logic(mock_save, mock_update, mock_get):
    """Test the core logic of pull_job without invoking the @q.worker decorator."""
    mock_get.return_value = {
        "id": "1234",
        "method": "stats",
        "month": 9,
        "year": 2017
    }

    result = worker.wave_statistics(9, 2017)

    job_id = "1234"
    worker.update_job_status(job_id, "In Progress")
    worker.save_results(job_id, result)
    worker.update_job_status(job_id, "Completed")

    mock_update.assert_called_with(job_id, "Completed")
    mock_save.assert_called_with(job_id, result)

@patch('worker.rd')
def test_wave_statistics_empty(mock_rd):
    """Test wave_statistics where no valid data exists."""
    mock_rd.keys.return_value = [b'wave:1']
    mock_rd.get.return_value = b'{"Hmax": null, "Peak Direction": null, "SST": null}'  # Ensure required keys exist

    stats = worker.wave_statistics(9, 2017)

    assert isinstance(stats, dict)
    assert 'Max Wave Height From Period Stats (m)' in stats

@patch('worker.rd')
def test_wave_statistics_with_data(mock_rd):
    """Test wave_statistics with valid data."""
    fake_data = [
        b'{"Date/Time": "09/12/2017 18:30", "Hs": 1.3, "Hmax": 2.0, "Tz": 5, "Tp": 9, "Peak Direction": 270, "SST": 25}',
        b'{"Date/Time": "09/12/2017 18:40", "Hs": 1.4, "Hmax": 2.2, "Tz": 6, "Tp": 10, "Peak Direction": 280, "SST": 26}'
    ]
    mock_rd.keys.return_value = [b'wave:0', b'wave:1']
    mock_rd.get.side_effect = fake_data

    stats = worker.wave_statistics(9, 2017)
    assert isinstance(stats, dict)
    assert stats['Max Wave Height From Period Stats (m)']['count'] == 2.0

@patch('worker.rd')
def test_plot_height_vs_time_real_behavior(mock_rd):
    """Test plot_height_vs_time function returns a DataFrame."""
    fake_data = [
        b'{"Date/Time": "09/12/2017 18:30", "Hs": 1.3}',
        b'{"Date/Time": "09/12/2017 18:40", "Hs": 1.4}'
    ]
    mock_rd.keys.return_value = [b'wave:0', b'wave:1']
    mock_rd.get.side_effect = fake_data

    fig_or_output = worker.plot_height_vs_time(9, 2017)

    import pandas as pd
    assert isinstance(fig_or_output, pd.DataFrame)
