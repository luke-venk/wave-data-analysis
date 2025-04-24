from flask import Flask, request
from redis import Redis
from hotqueue import HotQueue
import os
import logging
import requests
import pandas as pd
import json
from datetime import datetime
import zipfile
from io import BytesIO
from jobs import add_job, get_job_by_id, get_results_by_id


########## CONFIG ##########
# Environment variables
_redis_ip = os.environ.get('REDIS_HOST_IP')  # Environment variable for Redis IP address
_redis_port = 6379

# Flask and database configuration
app = Flask(__name__)
rd = Redis(host=_redis_ip, port=_redis_port, db=0)  # Database for wave data
q = HotQueue('queue', host=_redis_ip, port=_redis_port, db=1)  # Queue for job IDs
jdb = Redis(host=_redis_ip, port=_redis_port, db=2)  # Database for jobs data
resdb = Redis(host=_redis_ip, port=_redis_port, db=3)  # Database for job results data

# Logging configuration
_log_level = os.environ.get('LOG_LEVEL')  # Environment variable for logging level
logging.basicConfig(level=_log_level)
logging.debug('Flask app is up and running.')


########## URL ROUTES ##########
@app.route('/', methods=['GET'])
def index() -> tuple[str, int]:
    '''
    Prints hello world. Simply used to confirm app is
    up and running. Returns HTTP status code "I'm a teapot."
    '''
    return 'Hello, world!\n', 418

@app.route('/help', methods=['GET'])
def help() -> tuple[str, int]:
    '''
    Describes all routes within the app with short descriptions.
    '''
    # TODO: @Gabriel

@app.route('/data', methods=['POST', 'GET', 'DELETE'])
def data() -> tuple[str, int]:
    '''
    This function accepts 3 different request methods.
    
    POST: 
    If the Redis database is empty, loads the wave data into 
    the database. Uses the requests library to get the data directly 
    from the web in JSON format.
    
    GET:
    Returns all the data in the Redis database to the user in the
    form of a JSON list.
    
    DELETE:
    Deletes all the data in the Redis database.
    
    Arguments: None
    Returns: 
        output (str):
            POST: confirmation that data has been loaded (Status code 201)
            GET: all the data in the form of a JSON list
            DELETE: confirmation that data has been deleted
        status code (int):
            200: Request succeeded
            201: Resource created
            204: No content
            405: Method not allowed
    '''
    output = ''
    status_code = 204
    if request.method == 'POST':
        # If database is empty, populate it using link
        if rd.dbsize() == 0:
            logging.debug('Database empty. Populating database now.')
            
            # TODO @Tavishka
            url = "https://www.kaggle.com/api/v1/datasets/download/jolasa/waves-measuring-buoys-data-mooloolaba?datasetVersionNumber=1"
            response = requests.get(url, allow_redirects=True)
            if response.status_code == 200:
                with zipfile.ZipFile(BytesIO(response.content), 'r') as zip_ref:
                    file_name = zip_ref.namelist()[0]
                    with zip_ref.open(file_name) as f:
                        df = pd.read_csv(f)
            else:
                return 'ERROR 404: Failed to download dataset from Kaggle.\n', 404
            
            df.replace(99.99, pd.NA, inplace=True)  # sanitize
            records = df.to_dict(orient='records')

            for i, record in enumerate(records):
                rd.set(f"wave:{i}", json.dumps(record))
            
            output = '201: Database has been successfully loaded with data.'
            status_code = 201

        else:
            output = '200: Database is already populated.'
            status_code = 200
    
    elif request.method == 'GET':
        logging.debug('Printing all data now.')
        
        # TODO @Tavishka
        keys = rd.keys('wave:*')
        wave_data_list = [json.loads(rd.get(key)) for key in keys]

        # return jsonify(wave_data_list), 200
        return wave_data_list, 200

    elif request.method == 'DELETE':
        logging.debug('Deleting database now.')
        rd.flushdb()
        output = '410: All data has been cleared from the database.'
        status_code = 410
    else:
        output = 'ERROR 405: Method not allowed.'
        status_code = 405
    return output + '\n', status_code

@app.route('/waves', methods=['GET'])
def get_closest_wave() -> tuple[str, int]:
    epoch = request.args.get("epoch")
    '''
    Returns JSON-formatted dictionary of the data corresponding
    to the wave data entry closest in time to the input epoch.
    
    Arguments: 
        epoch (str): The epoch for which the closest wave 
            data will be returned. Formatted as "MM/DD/YYYY hh:mm"
    Returns: 
        output (str): JSON formatted list of the data corresponding to that wave
        status code (int):
            200: Request succeeded
            400: Bad request
            404: Data not found
    '''
    if rd.dbsize() == 0:
        return 'ERROR 404: No data found in the database.\n', 404
    
    # TODO: @Tavishka
    try:
        input_time = datetime.strptime(epoch, "%m/%d/%Y %H:%M")
            
        keys = rd.keys("wave:*")
        if not keys:
            return "ERROR 404: No wave data entries found.\n", 404
            
        closest_record = None
        min_time_diff = float('inf')
            
        for key in keys:
            record = json.loads(rd.get(key))
            record_time_str = record.get("Date/Time")
            if not record_time_str:
                continue
                
            try:
                record_time = datetime.strptime(record_time_str, "%m/%d/%Y %H:%M")
                time_diff = abs((record_time - input_time).total_seconds())
                    
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_record = record
                
            except ValueError:
                continue  # Skip invalid formats
                    
        if closest_record:
            return json.dumps(closest_record), 200
        else:
            return "ERROR 404: No valid timestamps found in data.\n", 404
        
    except ValueError:
        return "ERROR 400: Bad request. Use format 'MM/DD/YYYY HH:MM'.\n", 400

    
@app.route('/jobs', methods=['POST', 'GET'])
def jobs() -> tuple[str, int]:
    '''
    This function accepts 2 different request methods.
    
    POST: 
    Creates a new job with a unique identifier (uuid). The POST
    request must include a data packet in JSON format, which
    is stored along with the job information. The data should 
    be formatted like '{"month": MM, "year": YYYY, "method": "<method>"}'.
    
    GET:
    Lists all existing job IDs.
    
    Arguments: None
    Returns: 
        output (str):
            POST: confirmation that data has been loaded
            GET: a list of all the existing job IDs
        status code (int):
            200: Request succeeded
            201: Resource created
            204: No content
            400: Bad request
            404: Not found
            405: Method not allowed
    '''
    output = ''
    status_code = 204
    if request.method == 'POST':
        data = request.get_json()
        # Ensure the user gave a request that included the valid data
        if not data or 'month' not in data or 'year' not in data or 'method' not in data:
            return 'ERROR 400: Bad request. Please make sure that "month", "year", and "method" are all in the request.\n', 400
        
        month = data['month']
        year = data['year']
        method = data['method']
        
        # Ensure the user input valid types
        if not isinstance(month, int) or not isinstance(year, int):
            return 'ERROR 400: Bad request. Please ensure that both "month" and "year" are input as integer values.\n', 400
        
        # Ensure that database is not empty
        if rd.dbsize() == 0:
            return 'ERROR 404: No data found in the database.\n', 404
        
        # Ensure user input a valid month and year value
        if not (1 <= month <= 12):  
            return 'ERROR 400: Bad request. Please ensure you input a valid value for "month".\n', 400
        if not (1900 <= year <= 2100):  
            return 'ERROR 400: Bad request. Please ensure you input a valid value for "year".\n', 400
        
        # Create new job with a UUID and store as dictionary
        job_dict = add_job(month, year, method)  # Status will be Pending
        job_id = job_dict['id']
        job_status = job_dict['status']
        
        output = f'Job {job_id} successfully created. Status is {job_status}.\n'
        status_code = 201
        return output, status_code
    
    elif request.method == 'GET':
        # Ensure that jobs database is not empty
        if jdb.dbsize() == 0:
            return 'ERROR 404: No jobs have been found in the database.\n', 404
        else:
            output = 'Here is a list of all current job IDs:\n'
            job_ids = jdb.keys()
            for index, job_id in enumerate(job_ids):
                job_dict = get_job_by_id(job_id)
                output += f'  Job {index+1}. {job_id.decode()}\n'
            status_code = 200
            return output, status_code
    
    return 'ERROR 405: Method not allowed.\n', 405

@app.route('/jobs/<string:job_id>', methods=['GET'])
def get_job_info(job_id: str) -> tuple[str, int]:
    '''
    Given a job ID, return all job information 
    related to that specific job.
    
    Argument:
        job_id (str): The job's ID
    Returns:
        job_info (str): The job's information
        status code (int):
            200: Request succeeded
            404: Not found
            405: Method not allowed
    '''
    output = ''
    status_code = -1
    if request.method == 'GET':
        # Check that user input a valid job ID
        if job_id not in [key.decode('utf-8') for key in jdb.keys()]:
            return '404: Job not found. Please ensure you enter a valid job ID.\n', 404
        else:
            job_dict = get_job_by_id(jid=job_id)
            output = 'Here is all the information related to the job you requested: \n'
            output += '  Job ID:        ' + job_dict['id'] + '\n'
            output += '  Status:        ' + job_dict['status'] + '\n'
            output += '  Month:    ' + str(job_dict['month']) + '\n'
            output += '  Year:     ' + str(job_dict['year']) + '\n'
            output += '  Method:         ' + job_dict['method'] + '\n'
            status_code = 200
            return output, status_code
    else:
        return 'ERROR 405: Method not allowed.\n', 405
    
@app.route('/results/<string:job_id>', methods=['GET'])
def get_job_results(job_id: str) -> tuple[str, int]:
    '''
    Given a job ID, return the results of that specific job. More
    specifically, every gene that was approved in a year in the
    time frame corresponding to that job will be output to the user.
    
    Argument:
        job_id (str): The job's ID
    Returns:
        output (str): The results of the job
        status code (int):
            200: Request succeeded
            202: Request accepted but still in progress
            404: Not found
            405: Method not allowed
    '''
    logging.debug(f'Getting results for job {job_id}')
    output = ''
    status_code = -1
    if request.method == 'GET':
        # Check that user input a valid job ID
        if job_id not in [key.decode('utf-8') for key in jdb.keys()]:
            return '404: Job not found. Please ensure you enter a valid job ID.\n', 404
        else:
            job_dict = get_job_by_id(jid=job_id)
            status = job_dict['status']
            month = str(job_dict['month'])
            year = str(job_dict['year'])
            method = job_dict['method']
            
            if status == 'Completed':
                logging.debug('Printing job results to user.')
                results = get_results_by_id(job_id)
                
                # TODO: @Luke
                if method == 'stats':
                    pass
                elif method == 'plot':
                    pass
                
                status_code = 200
            else:
                logging.debug("Job's not finished. Job finished? I don't think so.\n-Kobe Bryant")
                output = 'The job has not been finished yet. Please try again in a few seconds.\n'
                status_code = 202
                
            return output, status_code
    else:
        return 'ERROR 405: Method not allowed.\n', 405
        
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
