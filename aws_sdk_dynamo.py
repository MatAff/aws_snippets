
# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.Python.html

import json
import os
from pprint import pprint

import boto3
from botocore.exceptions import ClientError
import pandas as pd

# settings
table_name = 'my_table'

dy_client = boto3.client('dynamodb')
dy_res = boto3.resource('dynamodb')

# list tables 
dy_client.list_tables()

# create table
table = dy_res.create_table(
    TableName = table_name,
    KeySchema=[
        {
            'AttributeName': 'key',
            'KeyType': 'HASH'  # Partition key
        },
        {
            'AttributeName': 'text',
            'KeyType': 'RANGE'  # Sort key
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'key',
            'AttributeType': 'N'
        },
        {
            'AttributeName': 'text',
            'AttributeType': 'S'
        },
    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    }
)

# add item
item = {
    'key': 0, 
    'text': 'zero',
    'stuff': {
        'message': 'hello word',
        'response': 'oh hello',
    },
}
table = dy_res.Table(table_name)
table.put_item(Item=item)

# read item
table = dy_res.Table(table_name)
try:
    response = table.get_item(Key={'key': 0, 'text': 'zero'})
except ClientError as e:
    print(e.response['Error']['Message'])
else:
    print(response['Item'])

# update item
table = dy_res.Table(table_name)
response = table.update_item(
    Key={
        'key': 0,
        'text': 'zero'
    },
    UpdateExpression="set stuff.message=:r",
    ExpressionAttributeValues={
        ':r': 'hello again',
    },
    ReturnValues="UPDATED_NEW"
)
response

# delete item
table = dy_res.Table(table_name)
try:
    response = table.delete_item(
        Key={
            'key': 0,
            'text': 'zero'
        },
    )
except ClientError as e:
    print(e.response['Error']['Message'])
else:
    print(response)

# # conditional deletion example
# try:
#     response = table.delete_item(
#         Key={
#             'year': year,
#             'title': title
#         },
#         ConditionExpression="info.rating <= :val",
#         ExpressionAttributeValues={
#             ":val": Decimal(rating)
#         }
#     )
# except ClientError as e:
#     if e.response['Error']['Code'] == "ConditionalCheckFailedException":
#         print(e.response['Error']['Message'])
#     else:
#         raise
# else:
#     return response

# delete table
dy_client.delete_table(TableName=table_name)