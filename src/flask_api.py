from flask import Flask, request, jsonify, send_file
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
from worker import plot_height_vs_time
from matplotlib import pyplot as plt
from dateutil import parser

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
    """
    Describes all routes within the app with short descriptions.
    """
    help_text = """
    Wave Data Analysis API - Available Endpoints:

GET    /help               : Prints available routes with a short description
GET    /data               : Retrieves all data currently stored in the Redis database
POST   /data               : Pulls current data from Kaggle and loads it into the Redis database
DELETE /data               : Deletes all data currently stored in the Redis database
GET    /waves?epoch=<str>  : Finds the closest wave data entry to the given epoch time string
GET    /jobs               : Lists all active jobs in the jobs database
GET    /jobs/<job_id>      : Retrieves information for a specific job by unique ID
GET    /results/<job_id>   : Retrieves results for a specific job by unique ID
GET    /download/<job_id>  : Downloads the output plot for a specific job by unique ID
"""
    return (help_text.strip(), 200)


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
            404: Data not found
            405: Method not allowed
    '''
    output = ''
    status_code = 204
    if request.method == 'POST':
        # If database is empty, populate it using link
        if rd.dbsize() == 0:
            logging.debug('Database empty. Populating database now.')

            url = 'https://www.kaggle.com/api/v1/datasets/download/jolasa/waves-measuring-buoys-data-mooloolaba?datasetVersionNumber=1'
            response = requests.get(url, allow_redirects=True)
            if response.status_code == 200:
                with zipfile.ZipFile(BytesIO(response.content), 'r') as zip_ref:
                    file_name = zip_ref.namelist()[0]
                    with zip_ref.open(file_name) as f:
                        df = pd.read_csv(f)
                logging.debug('Database populated successfully.')
            else:
                logging.error('Failed to download dataset from Kaggle.')
                return 'ERROR 404: Failed to download dataset from Kaggle.\n', 404

            # Clean and format
            df.replace(99.99, pd.NA, inplace=True)
            df.replace(-99.99, pd.NA, inplace=True)
            # Sort by timestamp
            df.sort_values(by=df.columns[0], inplace=True)

            # Store in Redis using the timestamp as the key
            # The other colums will be the value
            rd_keys = df.iloc[:, 0]
            rd_values = df.iloc[:, 1:]

            for key, row in zip(rd_keys, rd_values.to_dict(orient='records')):
                rd.set(key, json.dumps(row))

            output = '201: Database has been successfully loaded with data.'
            status_code = 201

        else:
            output = '200: Database is already populated.'
            status_code = 200

    elif request.method == 'GET':
        if rd.dbsize() == 0:
            return 'ERROR 404: No data found in the database.\n', 404
        else:
            logging.debug('Printing all data now.')
            all_data = {}
            for key in rd.keys():
                all_data[key.decode()] = json.loads(rd.get(key))

            return jsonify(all_data), 200

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
    '''
    Returns JSON-formatted dictionary of the data corresponding
    to the wave data entry closest in time to the input epoch.

    Query parameter:
        epoch (str): The target timestamp. Accepts formats like "MM/DD/YYYY HH:MM"
    
    Returns:
        JSON response of the closest wave record
    '''
    epoch = request.args.get('epoch')
    if rd.dbsize() == 0:
        return 'ERROR 404: No data found in the database.\n', 404

    try:
        input_time = parser.parse(epoch)
        keys = rd.keys()

        if not keys:
            return 'ERROR 400: Missing required query parameter: epoch.\n', 400

        closest_record = None
        min_time_diff = float('inf')

        for key in keys:
            try:
                record_time_str = key.decode()
                record_time = parser.parse(record_time_str)
                time_diff = abs((record_time - input_time).total_seconds())

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_record = json.loads(rd.get(key))
            except Exception:
                continue  # skip bad formats

        if closest_record:
            return jsonify(closest_record), 200
        else:
            return 'ERROR 404: No valid timestamps found in data.\n', 404

    except Exception:
        return 'ERROR 400: Bad request. Use format "MM/DD/YYYY HH:MM".\n', 400

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
        if (
            not data
            or 'month' not in data
            or 'year' not in data
            or 'method' not in data
        ):
            return (
                'ERROR 400: Bad request. Please make sure that "month", "year", and "method" are all in the request.\n',
                400,
            )

        month = data['month']
        year = data['year']
        method = data['method']

        # Ensure the user input valid types
        if not isinstance(month, int) or not isinstance(year, int):
            return (
                'ERROR 400: Bad request. Please ensure that both "month" and "year" are input as integer values.\n',
                400,
            )

        # Ensure that database is not empty
        if rd.dbsize() == 0:
            return 'ERROR 404: No data found in the database.\n', 404

        # Ensure user input a valid month and year value
        if not (1 <= month <= 12):
            return (
                'ERROR 400: Bad request. Please ensure you input a month between 1 and 12.\n',
                400,
            )
        if not (2017 <= year <= 2019):
            return (
                'ERROR 400: Bad request. Please ensure you input a year between 2017 and 2019.\n',
                400,
            )

        # Ensure user inputs a valid method
        if method not in ['stats', 'plot']:
            return (
                'ERROR 400: Bad request. Please ensure your method is either "stats" or "plot".\n',
                400,
            )

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
            output += '  Month:         ' + str(job_dict['month']) + '\n'
            output += '  Year:          ' + str(job_dict['year']) + '\n'
            output += '  Method:        ' + job_dict['method'].capitalize() + '\n'
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
            303: See other
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

            if job_dict['method'] == 'stats':
                if job_dict['status'] == 'Completed':
                    logging.debug('Printing job results to user.')
                    results = get_results_by_id(job_id)
                    results = [results] if not isinstance(results, list) else results
                    return jsonify(results), 200
                    
                else:
                    logging.debug(
                        "Job's not finished. Job finished? I don't think so.\n-Kobe Bryant"
                    )
                    output = 'The job has not been finished yet. Please try again in a few seconds.\n'
                    status_code = 202
            elif job_dict['method'] == 'plot':
                return (
                    "The job you are looking for is a 'plot' method, so use the /download route.\n",
                    302,
                )

            return output, status_code
    else:
        return 'ERROR 405: Method not allowed.\n', 405


@app.route('/download/<string:job_id>', methods=['GET'])
def download(job_id):
    '''
    Given a job ID, downloads the plot of that specific job.

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
    # First, ensure job exists
    if job_id not in [key.decode('utf-8') for key in jdb.keys()]:
        return '404: Job not found. Please ensure you enter a valid job ID.\n', 404
    else:
        job_dict = get_job_by_id(job_id)

        # Second, ensure the job has completed
        if job_dict['status'] != 'Completed':
            return f'Job {job_id} has not completed yet.', 202

        # Third, ensure that the job actually had the method "plot"
        if job_dict['method'] == 'plot':
            file_path = f'/plots/histogram_{job_id}.png'
            with open(file_path, 'wb') as f:
                f.write(resdb.hget(job_id, 'plot'))
            return send_file(file_path, mimetype='image/png', as_attachment=True), 200
        else:
            return "This job's method was not plot.", 405


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
