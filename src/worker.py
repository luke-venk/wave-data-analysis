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
    month = str(job_dict['month'])
    year = str(job_dict['year'])
    method = str(job_dict['method'])
    
    # Ensure not empty job
    if job_dict is None:
        logging.warning(f'Job {job_id} is missing from jdb. Skipping.')
        return
    
    update_job_status(job_id, status='In Progress')
    
    if method == 'stats':
        output = wave_statistics(month, year)
    elif method == 'plot':
        output = plot_height_vs_time(month, year)
    
    save_results(job_id, output)  # Save results to Redis database
    update_job_status(job_id, status='Completed')
    
def wave_statistics(month, year):
    '''
    Prints various summary statistics for all the waves in a 
    user-specified time period. Wave characteristics include 
    wave height, period, direction, and temperature. Statistics
    include median, high, low, and standard deviation.
    
    Arguments: 
        month_year (str): The month and year of the time period of which
            the user is querying statistics. Formatted as "MM-YYYY"
    Returns: 
        output (str): Summary statistics of the waves in that time period
    '''
    # TODO: @Gabriel
    try:
        month = int(month)
        year = int(year)
        keys = rd.keys('waves:*')
        data = [json.loads(rd.get(key)) for key in keys] # Use keys to parse database and load the list of dictionaries
        wave_df = pd.DataFrame(data)
        wave_df['Date/Time'] = pd.to_datetime(wave_df['Date/Time'], format='%d/%m/%Y %H:%M') # Convert to datetime python object for easier parsing

        wave_month_year_raw = wave_df[(wave_df['Date/Time'].dt.month == month) & (wave_df['Date/Time'].dt.year == year)]
        wave_month_year_stats = wave_month_year_raw[['Hmax', 'Peak Direction', 'SST']].describe()
        wave_month_year_stats_dict = wave_month_year_stats.to_dict()
        return wave_month_year_stats_dict


    except ValueError:
        return '''ERROR 400: Bad request. Use format '{"month": MM, "year": YYYY, "method": "<method>"}', 400'''
    
def plot_height_vs_time(month, year):
    '''
    Plots 2D histogram of height vs. time for all the waves in a 
    user-specified time period. The function will utilize Matplotlib
    and save the plot to file, allowing the user to see high tide and 
    low tide throughout the year.
    
    Arguments: 
        month_year (str): The month and year of the time period of which
            the user is querying statistics. Formatted as "MM-YYYY"
    Returns: 
        output (str): Message either confirming the operation 
            either succeeded or failed.
    '''
    # TODO: @Gabriel
    
if __name__ == '__main__':
    for _ in range(15):
        try:
            pull_job()
        except BusyLoadingError:
            logging.warning('Redis database not fully loaded, trying again in 1 second...')
            time.sleep(1)