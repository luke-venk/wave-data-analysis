# Analysis of Oceanographic Wave Data from Buoys
TODO: @Tavishka

## Description
Adding onto our previous assignment, which used a containerized Flask app and a Redis database to allow the user to query information related to the HGNC and supported concurrency, we update the worker script to do some actual analysis. Using user input and pulling from the raw data, the worker will do some analysis and the user will be able to query the results for a given job.

https://www.kaggle.com/datasets/jolasa/waves-measuring-buoys-data-mooloolaba?resource=download

## Program Requirements
### Dataset
There is no need for the user to download the data manually. Instead, the program will dynamically request the data at runtime, if not loaded into the Redis database already, from the following URL:  
https://storage.googleapis.com/public-download-files/hgnc/json/json/hgnc_complete_set.json  

The fields included in the dataset are related unique genes, including data like HGNC ID (a unique identifier for each gene), symbol, name, and key dates related to when these data were set. There are over 40,000 entries, each of which has many fields of data.

### Dependencies
To simplify working with dependencies, I containerize my application. Furthermore, I use requirements.txt to simplify dependency management within my container. My program makes use of the following libraries that are not in the Python standard library. These are all included in requirements.txt, which is copied to the container, and the libraries are recursively installed.

## Software Diagram
![Software Diagram](diagram.jpg)

## Building the Docker Image
Before running, you need to ensure ports 5000 and 6379 on your host machine is not already allocated. If there is another container running on that port, remove that container. You can remove all containers on your host machine with the following command:  
```docker rm -f `docker ps -aq` ```

In this repository, I include the docker-compose.yml file and Dockerfile. First, in your terminal, navigate into the homework08 directory. Then, to build the image, run the following:  
```docker compose up```

## Running the Application
Once you have built the Docker image, you can run the containers and either use the routes to query data, or run the unit tests. By default, Dockerfile specifies the default command to run the Flask app. Thus, there is no need to manually run the app.  

## Accessing URL routes
To retrieve useful information from the Flask app, we use curl to access routes. Here are the commands you should use. Ensure that you are executing these from a separate terminal from which you ran docker compose.   

### Working with HGNC data
To populate the database, enter the following:  
```curl -X POST localhost:5000/data```  
Keep in mind that if the database is not already populated, this could take several moments. You will receive a message confirming whether the operation was successful or not.  

To return all the data from the database in the form of a JSON list, enter the following:  
```curl -X GET localhost:5000/data``` or equivalently, ```curl localhost:5000/data```  
If the operation was unsuccessful, a message will confirm what specifically the error was.  

To clear the database, enter the following:  
```curl -X DELETE localhost:5000/data```  
You will receive a message confirming that the operation was successful.  

To return a JSON-formatted list of all hgnc_id fields, enter the following:  
```curl localhost:5000/genes```  

To return a JSON-formatted list of all the data associated with a given hgnc_id, enter the following:  
```curl localhost:5000/genes/<HGNC_ID>```  
For example,  
```curl localhost:5000/genes/HGNC:3575```  
If the inputted ID is valid, all the data will be output in a JSON-formatted list. Otherwise, a message confirming the error will be presented.  

### Working with jobs
To create a new job, execute the following POST command. Note that this command will return the genes who were approved in the given time frame. Please ensure both years and the limit are integer values:  
```curl localhost:5000/jobs -X POST -d '{"month": MM, "year": YYYY, "method": "<method>"}' -H "Content-Type: application/json"```  
For example:  
```curl localhost:5000/jobs -X POST -d '{"start_year": 2007, "end_year": 2009, "limit": 10}' -H "Content-Type: application/json"```  
If the operation is successful, a message will be output confirming the job was created, and that its status is Pending. The status will be updated to "Complete" once the job is finished. Note that the operation will be successful if parameters are invalid. An example output would be the following:  
```Job a0987630-8db3-4cf1-8152-c5bed6ac6e65 successfully created. Status is Pending.```

To return a list of all the job IDs, run the following command:  
```curl localhost:5000/jobs```   
Note that due to how Redis hashes its data, the jobs will not necessarily be returned in the order they were submitted.

To return the information corresponding to a specific job ID, run the following command:  
```curl localhost:5000/jobs/<job_id>```   
For example:
```curl localhost:5000/jobs/a0987630-8db3-4cf1-8152-c5bed6ac6e65```   
An example output would be the following:  
<code>
Here is all the information related to the job you requested: 
  Job ID:        a0987630-8db3-4cf1-8152-c5bed6ac6e65
  Status:        Completed
  Start Year:    2007
  Last Year:     2009
  Limit:         10
</code>  

### Getting the Results of a Job
To find the results of a job you submitted, run the following command:  
```curl localhost:5000/results/<job_id>```  
For example:
```curl localhost:5000/results/276aec08-d0de-48ca-b0c5-29a076b6e3f2```   
An example output would be the following:  
<code>
Here are the first 10 the genes that were approved between 2007 and 2009.
	HGNC:37133
	HGNC:24086
	HGNC:25662
	HGNC:33842
	HGNC:23993
	HGNC:34405
	HGNC:33352
	HGNC:33353
	HGNC:26971
	HGNC:34041
	HGNC:34042
</code>  
If the operation is successful, the job ID, status, first HGNC ID, and last HGNC ID will be outputted. Otherwise, an error message will be presented.  

## Running the Unit Tests
The tests, which utilize pytest, are automatically ran when ```docker compose up --build``` is executed. These tests compose of unit and integration tests. Please note that these tests might take up to 60 seconds to complete. If you would like to see the results of these automated tests, you may run the following:  
```docker logs homework08-tests-1```  
Note that _homework08-tests-1_ is the name of your docker container running the tests, which you can confirm using ```docker ps -a```.

## Cleanup
When you are done using the app, you can stop the Flask app using Ctrl+C. Take care to stop the Flask, Redis, and worker containers from running on your localhost:  
```docker compose down ```