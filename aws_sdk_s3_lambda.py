
""""
Goal: Create a s3 file upload triggered lambda
"""

import json
import zipfile

import boto3
import pandas as pd

# --- SETTINGS 

lambda_name = 'textToUpperTwo'
policy_name = 'AWSLambdaBasicExecutionRoleForTextToUpperTwo'
role_name = 'lambda_role_text_to_upper'

tags = [
    {'Key': 'purpose', 'Value': 'aws_exploration'},
    {'Key': 'temporary', 'Value': 'true'},
]

bucket_name = 'sample-bucket-afasfsagad'
bucket_name_lambda = 'lambda-function-bucket-ghagkdl'

# --- S3 ---

# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-examples.html

s3_client = boto3.client('s3')
s3_res = boto3.resource('s3')

# list buckets
buckets = s3_client.list_buckets()
buckets_df = pd.DataFrame(buckets['Buckets'])
buckets_df

# create buckets
s3_client.create_bucket(Bucket=bucket_name)
s3_client.create_bucket(Bucket=bucket_name_lambda)

# --- IAM ---

iam_client = boto3.client('iam')

# define policy
policy_document = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:us-east-1:470008614845:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                f"arn:aws:logs:us-east-1:470008614845:log-group:/aws/lambda/{lambda_name}:*"
            ]
        },
                {
            "Sid": "ListObjectsInBucket",
            "Effect": "Allow",
            "Action": ["s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{bucket_name}"]
        },
        {
            "Sid": "AllObjectActions",
            "Effect": "Allow",
            "Action": "s3:*Object*",
            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
        }
    ]
})

# create policy
iam_client.create_policy(
    PolicyName=policy_name,
    PolicyDocument=policy_document,
    Tags=tags,
)

# list roles
role_df = pd.DataFrame(iam_client.list_roles()['Roles'])
role_df

# locate policy
policies_df = pd.DataFrame(iam_client.list_policies()['Policies'])
policy_arn = policies_df[policies_df.PolicyName==policy_name].Arn.iloc[0]
print(policy_arn)

# define assume role policy document
LAMBDA_ROLE = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
        "Effect": "Allow",
        "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
        }
    ]
})

# create role
role_response = iam_client.create_role(
    RoleName=role_name,
    AssumeRolePolicyDocument=LAMBDA_ROLE,
    Description=role_name,
    MaxSessionDuration=3600,
    Tags=tags,
)

# get role arn
role_df = pd.DataFrame(iam_client.list_roles()['Roles'])
role_arn = role_df[role_df.RoleName==role_name].Arn.iloc[0]
print(role_arn)

# attach policy
iam_client.attach_role_policy(
    RoleName=role_name, 
    PolicyArn=policy_arn
)

# --- LOG GROUPS ---

logs_client = boto3.client('logs')

response_lg = logs_client.create_log_group(
    logGroupName=f'/aws/lambda/{lambda_name}',
    # kmsKeyId='string',
    tags=tags[0]
)
response_lg

# --- LAMBDA --- 

ld_client = boto3.client('lambda')

# list functions
functions_df = pd.DataFrame(ld_client.list_functions()['Functions'])
functions_df

# # define function
# code_content = """
# import json

# def lambda_handler(event, context):
#     # TODO implement
#     return {
#         'statusCode': 200,
#         'body': json.dumps('Hello from Lambda!')
#     }

# """

code_content = """
import json
import boto3

# boto3 S3 initialization
s3_client = boto3.client("s3")
s3_res = boto3.resource('s3')

def lambda_handler(event, context):

    # log event
    print(event)

    # log context
    print(context)

    # get object details
    source_bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key_name = event['Records'][0]['s3']['object']['key']
    print(source_bucket_name, file_key_name)

    # load object
    obj = s3_res.Object(source_bucket_name, file_key_name)
    text = obj.get()['Body'].read()

    if text.upper() != text:

        # alter
        text = text.upper()
        print(text)

        # put
        obj = s3_res.Object(source_bucket_name, file_key_name)
        obj.put(Body=text)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

"""

# zip and upload to s3 for use in lambda
open('code.py', 'w').writelines(code_content)
archive = zipfile.ZipFile('function.zip', 'w')
archive.write('code.py', './code.py')
archive.close()
s3_client.upload_file('function.zip', Bucket=bucket_name_lambda, Key='function.zip')

# https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html

# create function
response = ld_client.create_function(
    FunctionName=lambda_name,
    Description=lambda_name,
    Handler='code.lambda_handler',
    Publish=True,
    Role=role_arn, 
    Runtime='python3.9',
    Code={
        'S3Bucket': bucket_name_lambda,
        'S3Key': 'function.zip',
    },
)
response

# --- ADD S3 TRIGGER ---

# compile bucket arn
bucket_arn = f'arn:aws:s3:::{bucket_name}'
print(bucket_arn)

# add permission
response_add_permission = ld_client.add_permission(
    FunctionName=lambda_name,
    StatementId=lambda_name,
    Action='lambda:InvokeFunction',
    Principal='s3.amazonaws.com',
    SourceArn=bucket_arn,
)
response_add_permission

# response_get_policy = ld_client.get_policy(FunctionName='textToUpper')
# response_get_policy

# get function arn
functions_df = pd.DataFrame(ld_client.list_functions()['Functions'])
function_arn = functions_df[functions_df.FunctionName==lambda_name].FunctionArn.iloc[0]
print(function_arn)

# add trigger
response_trigger = s3_client.put_bucket_notification_configuration(
    Bucket=bucket_name,
    NotificationConfiguration= {
        'LambdaFunctionConfigurations':[
          {'LambdaFunctionArn': function_arn, 
          'Events': ['s3:ObjectCreated:*']}
        ]
    }
)
response_trigger

# --- ADD TEST FILE ---

for i in range(10):
    file_name = f'test_40{i}.txt'
    open(file_name, 'w').writelines(['hello'])
    s3_client.upload_file(file_name, Bucket=bucket_name, Key=file_name)

# check result
obj = s3_res.Object(bucket_name, file_name)
text = obj.get()['Body'].read()
print(text)

# --- CLEAN UP ---

# delete lambda
ld_client.delete_function(FunctionName=lambda_name)

# remove role
iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
iam_client.delete_role(RoleName=role_name)

# remove policy
iam_client.delete_policy(PolicyArn=policy_arn)

# remove log group
logs_client.delete_log_group(logGroupName=f'/aws/lambda/{lambda_name}')

# empty and delete buckets
bucket = s3_res.Bucket(bucket_name)
bucket.objects.all().delete()
s3_client.delete_bucket(Bucket=bucket_name)

# empty and delete lambda bucket
bucket = s3_res.Bucket(bucket_name_lambda)
bucket.objects.all().delete()
s3_client.delete_bucket(Bucket=bucket_name_lambda)
