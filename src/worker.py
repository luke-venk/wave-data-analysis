from redis import Redis
from redis.exceptions import BusyLoadingError
from hotqueue import HotQueue
from jobs import update_job_status, get_job_by_id, save_results
import os
import time
import logging
import pandas as pd
import json
from datetime import datetime



########## CONFIG ##########
# Environment variables
_redis_ip = os.environ.get('REDIS_HOST_IP')  # Environment variable for Redis IP address
_redis_port = 6379

# Database configuration
rd = Redis(host=_redis_ip, port=_redis_port, db=0)  # Database for wave data
q = HotQueue('queue', host=_redis_ip, port=_redis_port, db=1)  # Queue for job IDs
jdb = Redis(host=_redis_ip, port=_redis_port, db=2)  # Database for jobs data
resdb = Redis(host=_redis_ip, port=_redis_port, db=3)  # Database for job results data

# Logging configuration
_log_level = os.environ.get('LOG_LEVEL')  # Environment variable for logging level
logging.basicConfig(level=_log_level)
logging.debug('Worker is up and running.')

@q.worker
def pull_job(job_id: str):
    '''
    The worker watches the queue and pulls job IDs as they arrive. 
    When it pulls a job ID the queue, it should find the corresponding
    job information in the jobs database, and do the following:
        - Update the status to "In Progress"
        - TODO: Based on the method specified by the user, 
            perform that analysis
        - Update the status to "Completed"
    '''
    logging.debug(f'Worker is pulling job {job_id}.')
    job_dict = get_job_by_id(job_id)  # Get dictionary of job information
    logging.debug(f'job_dict is: {job_dict}')
    method = str(job_dict['method'])
    
    try:
        month = int(job_dict['month'])
        year = int(job_dict['year'])
    except ValueError:
        logging.error('ERROR: month and year arguments are not valid integer values.')
        return
    
    # Ensure not empty job
    if job_dict is None:
        logging.warning(f'Job {job_id} is missing from jdb. Skipping.')
        return
    
    update_job_status(job_id, status='In Progress')
    
    if method == 'stats':
        output = wave_statistics(month, year)
    elif method == 'plot':
        output = plot_height_vs_time(month, year)
    else:
        logging.error('ERROR: Invalid method for request. Should be "stats" or "plot".')
        return
    
    save_results(job_id, output)
    update_job_status(job_id, status='Completed')
    
def wave_statistics(month: int, year: int) -> str:
    '''
    Prints various summary statistics for all the waves in a 
    user-specified time period. Wave characteristics include 
    wave height, period, direction, and temperature. Statistics
    include median, high, low, and standard deviation.
    
    Arguments: 
        month (int): The month of the query
        year (int): The year of the query
            
    Returns: 
        output (str): Summary statistics of the waves in that time period
    '''
    # TODO: @Gabriel
    key_pattern = f"{month:02d}/*/{year} *"

    filtered_keys = rd.keys(key_pattern)
    
    results = {}

    for key in filtered_keys:
        key = key.decode('utf-8')  # Decode the byte string to a regular string
        data = rd.get(key)
        if data is not None:
            data = json.loads(data.decode('utf-8'))
            results[key] = data



    wave_df = pd.DataFrame.from_dict(results)
    wave_df = wave_df.transpose()
    hmax_stats = wave_df['Hmax'].describe()
    peak_direction_stats = wave_df['Peak Direction'].describe()
    sea_temp_stats = wave_df['SST'].describe()
    wave_month_year_stats_dict = {"Max Wave Height From Period Stats (m)": hmax_stats.to_dict(),
                                      "Peak Direction From Period Stats (degrees)": peak_direction_stats.to_dict(),
                                      "Sea Surface Temperature From Period Stats (degrees C)": sea_temp_stats.to_dict()}
        
    
    logging.info('Job (stats) successfully finished.')
    
    return wave_month_year_stats_dict
    
def plot_height_vs_time(month: int, year: int) -> str:
    '''
    Plots 2D histogram of height vs. time for all the waves in a 
    user-specified time period. The function will utilize Matplotlib
    and save the plot to file, allowing the user to see high tide and 
    low tide throughout the year.
    
    Arguments: 
        month (int): The month of the query
        year (int): The year of the query
    Returns: 
        output (str): Message either confirming the operation 
            either succeeded or failed.
        
        Also saves the plot to resdb database
    '''
    # TODO: @Gabriel
    return f'Placeholder output: {month}-{year}.'
    
if __name__ == '__main__':
    for _ in range(15):
        try:
            pull_job()
        except BusyLoadingError:
            logging.warning('Redis database not fully loaded, trying again in 1 second...')
            time.sleep(1)