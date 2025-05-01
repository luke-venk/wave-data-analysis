from redis import Redis
from redis.exceptions import BusyLoadingError, ConnectionError
from hotqueue import HotQueue
from jobs import update_job_status, get_job_by_id, save_results_stats, save_results_plot
import os
import time
import logging
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt


########## CONFIG ##########
# Environment variables
_redis_ip = os.environ.get('REDIS_HOST_IP', 'redis-db')  # Environment variable for Redis IP address
_redis_port = 6379

# Flask and database configuration
def connect_redis(db: int) -> Redis:
    for attempt in range(10):
        try:
            client = Redis(host=_redis_ip, port=_redis_port, db=db)
            client.ping()
            logging.debug(f'DB {db} connected to Redis on attempt {attempt+1}')
            return client
        except ConnectionError as e:
            logging.debug(f'DB {db} not ready (attempt {attempt+1})')
            time.sleep(2)
    logging.error(f'DB {db} not available after 10 attempts, exiting.')
    exit(1)


rd = connect_redis(0)  # Database for wave data
jdb = connect_redis(2)  # Database for jobs data
resdb = connect_redis(3)  # Database for job results data

# Retry HotQueue separately
for attempt in range(10):
    try:
        q = HotQueue('queue', host=_redis_ip, port=_redis_port, db=1)
        q._HotQueue__redis.ping()
        logging.debug('HotQueue is ready.')
        break
    except ConnectionError as e:
        logging.debug(f'HotQueue Redis not ready (attempt {attempt+1})')
        time.sleep(2)
else:
    logging.error('HotQueue Redis failed after 10 tries, exiting.')
    exit(1)

# Logging configuration
_log_level = os.environ.get('LOG_LEVEL')  # Environment variable for logging level
logging.basicConfig(level=_log_level)
logging.debug('Worker is up and running.')

# Create the /plots directory
os.makedirs('/plots', exist_ok=True)

@q.worker
def pull_job(job_id: str) -> None:
    '''
    The worker watches the queue and pulls job IDs as they arrive. 
    When it pulls a job ID the queue, it should find the corresponding
    job information in the jobs database, and do the following:
        - Update the status to "In Progress"
        - Based on the method specified by the user, perform that analysis
        - Update the status to "Completed"
    '''
    logging.debug(f'Worker is pulling job {job_id}.')
    job_dict = get_job_by_id(job_id)  # Get dictionary of job information
    method = str(job_dict['method'])
    
    # Parse month and year
    try:
        month = int(job_dict['month'])
        year = int(job_dict['year'])
    except ValueError:
        logging.error('ERROR: month and year arguments are not valid integer values.')
        update_job_status(job_id, status='Failed')
        return
    
    # Ensure not empty job
    if job_dict is None:
        logging.error(f'Job {job_id} is missing from jdb. Skipping.')
        update_job_status(job_id, status='Failed')
        return
    
    update_job_status(job_id, status='In Progress')
    
    if method == 'stats':
        stats_dict = wave_statistics(month, year)
        save_results_stats(job_id, stats_dict)
    
    elif method == 'plot':
        file_path = plot_height_vs_time(month, year, job_id)
        with open(file_path, 'rb') as f:
            plot_file = f.read()
        save_results_plot(job_id, plot_file)

    else:
        logging.error('ERROR: Invalid method for request. Should be "stats" or "plot".')
        update_job_status(job_id, status='Failed')
        return
    
    update_job_status(job_id, status='Completed')
    
def wave_statistics(month: int, year: int) -> dict:
    '''
    Prints various summary statistics for all the waves in a 
    user-specified time period. Wave characteristics include 
    wave height, period, direction, and temperature. Statistics
    include median, high, low, and standard deviation.
    
    Arguments: 
        month (int): The month of the query
        year (int): The year of the query
            
    Returns: 
        stats (dict): Summary statistics of the waves in that time period
    '''
    # Key pattern should be any timestamp that has the month and year specified by the user
    key_pattern = f'{month:02d}/*/{year} *'
    filtered_keys = rd.keys(key_pattern)
    
    # Store all wave data with our month and year in results dictionary
    results = {}
    for key in filtered_keys:
        key = key.decode('utf-8')
        data = rd.get(key)
        if data is not None:
            data = json.loads(data.decode('utf-8'))
            results[key] = data

    # Get descriptive statistics from our timeframe
    wave_df = pd.DataFrame.from_dict(results)
    wave_df = wave_df.transpose()
    hmax_stats = wave_df['Hmax'].describe()
    peak_direction_stats = wave_df['Peak Direction'].describe()
    sea_temp_stats = wave_df['SST'].describe()
    stats = {'Max Wave Height From Period Stats (m)': hmax_stats.to_dict(),
            'Peak Direction From Period Stats (degrees)': peak_direction_stats.to_dict(),
            'Sea Surface Temperature From Period Stats (degrees C)': sea_temp_stats.to_dict()}
        
    
    logging.info('Job (stats) successfully finished.')
    
    return stats
    
def plot_height_vs_time(month: int, year: int, job_id: str) -> str:
    '''
    Plots 2D histogram of height vs. time for all the waves in a 
    user-specified time period. The function will utilize Matplotlib
    and save the plot to file, allowing the user to see high tide and 
    low tide throughout the year.
    
    Arguments: 
        month (int): The month of the query
        year (int): The year of the query
    Returns: 
        file_path (str): The file path the plot was saved to
    '''
    key_pattern = f'{month:02d}/*/{year} *'

    filtered_keys = rd.keys(key_pattern)
    
    results = {}

    for key in filtered_keys:
        key = key.decode('utf-8')  # Decode the byte string to a regular string
        data = rd.get(key)
        if data is not None:
            data = json.loads(data.decode('utf-8'))
            results[key] = data
        
    wave_df = pd.DataFrame.from_dict(results).transpose()
    wave_df= wave_df[(wave_df['Hmax'] >= 0) & (wave_df['Hmax'] <= 100)]
    plt.hist(wave_df['Hmax'], bins=50)
    plt.xlabel('Height (m)')
    plt.ylabel('Frequency')
    plt.title(f'2D Histogram of Height for {month:02d}/{year}')
    
    file_path = f'/plots/histogram_{job_id}.png'
    plt.savefig(file_path)


    
    logging.debug(f'Histogram saved to {file_path}')
    logging.info('Job (plot) successfully finished.')
    
    return file_path
    
if __name__ == '__main__':
    while True:
        try:
            pull_job()
        except BusyLoadingError:
            logging.warning('Redis database not fully loaded, trying again in 1 second...')
            time.sleep(1)
            continue
        except ConnectionError as e:
            logging.error(f'Redis connection dropped in worker. Reconnecting in 2 seconds...')
            time.sleep(2)
            q = HotQueue('queue', host=_redis_ip, port=_redis_port, db=1)
            continue
        except Exception:
            logging.error('Unexpected error in worker, restarting pull_job() in 2 seconds...')
            time.sleep(2)
            continue