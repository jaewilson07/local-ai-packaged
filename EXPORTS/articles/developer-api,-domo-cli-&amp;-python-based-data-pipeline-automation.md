---
title: "DEVELOPER // API, Domo CLI &amp; Python based Data Pipeline Automation"
url: /c/developerdomocom-community-edition/developer-api-domo-cli-python-based-data-pipeline-automation
author: Jae Myong Wilson
published_date: May 14, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# DEVELOPER // API, Domo CLI &amp; Python based Data Pipeline Automation
**Author:** Jae Myong Wilson
**Published:** May 14, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBM2dFREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--f9bfa6704fc52192d3ef6f8cf74d861fce9b925d/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/9.png)

---

## Pipeline Automation in Domo using Python and PyDomo

Giuseppe Russo, Data Engineer @ Everli shares how to use Domo's PyDomo SDK to automate data pipeline execution with python at the [Domo IDEA Exchange](www.onyxreporting.com/schedule) hosted by Onyx Reporting
﻿

﻿

### sample domo_[creds.py](https://creds.py) ###

client_id = 'id'
client_secret = 'secret'

email = 'email'
password = 'password'

domo_instance = 'your_instance_name'

import domo_creds, json, requests, time
from pprint import pprint
from pydomo import Domo
from datetime import datetime as dt

""" A. GET DATAFLOW INFORMATION """
## 1. CONNECT TO THE DOMO API
auth_api = 'https://{}.[domo.com/api/content/v2/authentication'.format(domo_creds.domo_instance)](https://domo.com/api/content/v2/authentication'.format(domo_creds.domo_instance))
auth_body = json.dumps({
"method": "password",
"emailAddress": domo_[creds.email](https://creds.email),
"password": domo_creds.password
})
auth_headers = {'Content-Type'   : 'application/json'}
auth_response = [requests.post](https://requests.post)(auth_api, data = auth_body, headers = auth_headers)
session_token = auth_response.json()['sessionToken']

## 2. GET THE LIST OF DATAFLOWS
all_dataflow_api = 'https://{}.[domo.com/api/dataprocessing/v1/dataflows/'.format(domo_creds.domo_instance)](https://domo.com/api/dataprocessing/v1/dataflows/'.format(domo_creds.domo_instance))
all_dataflow_headers = {'Content-Type'   : 'application/json',
'x-domo-authentication'  : session_token}
all_dataflow_response = requests.get(url = all_dataflow_api, headers = all_dataflow_headers)
# For simplicity of the task, we are getting all dataflows who have only one output
dataflow_list = [dataflow for dataflow in all_dataflow_response.json() if dataflow['numOutputs'] == 1]
# pprint(dataflow_list)

## 3. RETRIEVE THE DATAFLOW OF OUR OUTPUT
output_id = '50a38dd3-dbee-46a9-a3fe-66614ad8f024' # Sample output in the domo-dojo instance
# Iterating through the dataflow list and get the dataflow whose output is our specific one
dataset_dataflows = [dataflow for dataflow in dataflow_list if dataflow['outputs'][0]['dataSourceId'] == output_id]
# Theoretically only one dataflow should have our output, so we should get the first (and only) element of the list
dataflow = dataset_dataflows[0]
# print("\033[32;1;4mDataflow json Structure\033[0m");
# pprint(dataflow)

""" B. CHECK THE STATUS OF THE INPUTS """
## 1. CONNECT TO PYDOMO
pydomo_conn = Domo(domo_creds.client_id, domo_creds.client_secret, api_host = '[api.domo.com](https://api.domo.com)')

## 2. RETRIEVE THE INPUTS OF THE DATAFLOW
dataflow_inputs = [dataset['dataSourceId'] for dataset in dataflow['inputs']]
# print("\033[32;1;4mInputs ids of the dataflow\033[0m");
# pprint(dataflow_inputs)

## 3. CREATE A FUNCTION RETURNING THE LAST UPDATE OF A DATASET
def get_update_time(dataset_id):
# The datasets object contains the list of all datasets in our instance.
# We extract the last update time from this structure for our dataset
update_date = pydomo_conn.datasets.get(dataset_id)['dataCurrentAt']
# We need to deal with the format of the update time we retrieve from pydomo
utc_update_date = dt.strptime(update_date,"%Y-%m-%dT%H:%M:%SZ")
return utc_update_date

""" C. WHEN ALL INPUTS ARE UP TO DATE RUN THE DATAFLOW """
## 1. GET UPDATE TIME OF THE OUTPUT DATASET
output_update = get_update_time(output_id)
# print("\033[32;1;4mDataflow's output last update time\033[0m");
# print(output_update)

## 2. CHECK IF ALL INPUTS ARE UPDATED
# Getting the number of updated inputs
updated_input = sum(1 for input in dataflow_inputs if get_update_time(input) > output_update)
# Getting the number of inputs (no matter their last update)
nr_inputs = len(dataflow_inputs)
# Looping until the number of updated inputs is equal to the number of inputs
# print("\033[32;1;4mCheck condition loop started\033[0m");
while(updated_input != nr_inputs):
# print('{} out of {} inputs are updated. Waiting for all inputs to be updated....'.format(updated_input, nr_inputs))
time.sleep(10)
# Every 10 seconds I compute again the number of updated inputs
updated_input = sum(1 for input in dataflow_inputs if get_update_time(input) > output_update)
# print("\033[32;1;4mAll input updated. Running the dataflow...\033[0m");

## 3. RUN THE DATAFLOW
dataflow_run_api = 'https://{}.[domo.com/api/dataprocessing/v1/dataflows/{}/executions'.format(domo_creds.domo_instance](https://domo.com/api/dataprocessing/v1/dataflows/{}/executions'.format(domo_creds.domo_instance), dataflow['id'])
dataflow_run_headers = {'Content-Type'   : 'application/json',
'x-domo-authentication'  : session_token}
[requests.post](https://requests.post)(url = dataflow_run_api, headers = dataflow_run_headers)
# print("\033[32;1;4mDataflow has been run!\033[0m");
