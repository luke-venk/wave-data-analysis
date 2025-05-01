import json
import uuid
from redis import Redis
from hotqueue import HotQueue
import os
import logging


########## CONFIG ##########
# Environment variables
_redis_ip = os.environ.get('REDIS_HOST_IP', 'redis-db')  # Environment variable for Redis IP address
_redis_port = 6379

# Database configuration
q = HotQueue('queue', host=_redis_ip, port=_redis_port, db=1)  # Queue for job IDs
jdb = Redis(host=_redis_ip, port=_redis_port, db=2)  # Database for jobs data
resdb = Redis(host=_redis_ip, port=_redis_port, db=3)  # Database for job results data

# Logging configuration
_log_level = os.environ.get('LOG_LEVEL')  # Environment variable for logging level
logging.basicConfig(level=_log_level)

########## PRIVATE ##########

def _generate_jid() -> str:
    '''
    Generates a pseudo-random identifier for a job.
    '''
    return str(uuid.uuid4())

def _instantiate_job(jid: str, status: str, month: int, year: int, method: str) -> dict:
    '''
    Creates the job object as a Python dictionary.
    '''
    return {'id': jid,
            'status': status,
            'month': month,
            'year': year,
            'method': method}
    
def _save_job(jid: str, job_dict: dict) -> None:
    '''
    Saves a job object in the Redis database.
    '''
    jdb.set(jid, json.dumps(job_dict))
    return

def _queue_job(jid: str) -> None:
    '''
    Adds a job to the HotQueue.
    '''
    q.put(jid)

########## PUBLIC ##########
    
def add_job(month: str, year:str, method: str, status='Pending'):
    '''
    Adds a job to the Redis queue.
    '''
    jid = _generate_jid()  # Generate UUID
    job_dict = _instantiate_job(jid, status, month, year, method)  # Save as Python dict
    
    _save_job(jid, job_dict)  # Save to jobs Redis database
    _queue_job(jid)  # Add job to HotQueue
    logging.debug(f'Adding job {jid} to queue.')
    
    return job_dict

def get_job_by_id(jid: str) -> dict:
    '''
    Returns dictionary for job, given the jid
    '''
    job_info = jdb.get(jid)
    if job_info is None:
        logging.warning(f'Warning: No existing job information for job ID {jid}')
    else:
        return json.loads(job_info)  # JSON to Python dictionary

def update_job_status(jid: str, status: str) -> None:
    '''
    Updates the status of the job with job id `jid` to status `status`.
    '''
    if jid is None:
        logging.warning(f'Job {jid} is None. Skipping.')
        return
    job_dict = get_job_by_id(jid)
    if job_dict:
        job_dict['status'] = status
        _save_job(jid, job_dict)  # Overwrites previous data
        logging.debug(f'Job {jid} status updated to {status}.')
    else:
        logging.warning(f'No valid job for {jid}')

def get_results_by_id(jid: str) -> list:
    '''
    Returns dictionary for results, given the jid
    '''
    logging.debug(f'Fetching results for job {jid}')
    return json.loads(resdb.get(jid))  # JSON to Python list

def save_results_stats(jid: str, stats: dict) -> None:
    '''
    For the stats job, saves stats dict in the Redis database as a JSON formatted string.
    '''
    resdb.set(jid, json.dumps(stats))
    logging.debug(f'Job (stats) {jid} results saved to database.')
    
def save_results_plot(jid: str, plot_file: bytes) -> None:
    '''
    For the plot job, saves plot image in the Redis database as hashed file.
    '''
    resdb.hset(jid, 'plot', plot_file)
    logging.debug(f'Job (plot) {jid} results saved to database.')