
import json
import os

import boto3

# --- SETTINGS ---

path_resources = './resources.json'

# --- RESOURCE TRACKING ---

if os.path.exists(path_resources):
    resource_dict = json.load(open(path_resources))
else:
    resource_dict = {'resources': []}

# --- DELETE ---

order = ['Vpc']