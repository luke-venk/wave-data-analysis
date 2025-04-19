import pytest
import requests
import time
import os
import logging


########## CONFIG ##########
BASE_URL = 'http://flask-app:5000'  # Base URL is based on Flask app container
_log_level = os.environ.get('LOG_LEVEL')
logging.basicConfig(level=_log_level)

########## INTEGRATION TESTS ##########

########## UNIT TESTS ##########

# TODO: @Tavishka