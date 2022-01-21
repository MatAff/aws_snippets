""""s3 file upload adds to SQS"""

import json

import boto3
import pandas as pd

# --- SETTINGS ---

tags = [
    {'Key': 'purpose', 'Value': 'aws_exploration'},
    {'Key': 'temporary', 'Value': 'true'},
]

bucket_name = 'sample-bucket-afasfsagad'
queue_name = "upload_queue"

# --- S3 ---

# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-examples.html

s3_client = boto3.client('s3')
s3_res = boto3.resource('s3')

# List buckets
buckets = s3_client.list_buckets()
buckets_df = pd.DataFrame(buckets['Buckets'])
buckets_df

# Create bucket
s3_client.create_bucket(Bucket=bucket_name)

# # Empty and delete buckets
# bucket = s3_res.Bucket(bucket_name)
# bucket.objects.all().delete()
# s3_client.delete_bucket(Bucket=bucket_name)

# --- SQS ---

sqs_client = boto3.client("sqs")
sqs_res = boto3.resource("sqs")

# List queue
queues = sqs_client.list_queues()
queue_df = pd.DataFrame(queues.get("QueueUrls", []))
queue_df

# Create a queue
queue_resp = sqs_client.create_queue(QueueName=queue_name, tags=tags[0])
queue_url = queue_resp["QueueUrl"]
queue_attributes = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
queue_arn = queue_attributes["Attributes"]["QueueArn"]
print(queue_arn)

# # Delete a queue
# sqs_client.delete_queue(QueueUrl=queue_url)

# --- IAM ---

# iam_client = boto3.client('iam')

# Define policy
policy_document = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "SQS:SendMessage",
            "Resource": queue_arn,
            "Condition": {"ArnLike": { "aws:SourceArn": f"arn:aws:s3:*:*:{bucket_name}"}},
            "Principal": {"AWS": "*"},

        }
    ]
})

# Set policy
sqs_client.set_queue_attributes(
    QueueUrl=queue_url,
    Attributes={'Policy': policy_document
    }
)

# --- EVENT ---

bucket_notifications_configuration = {
    'QueueConfigurations': [{
        'Events': ['s3:ObjectCreated:*'],
        'QueueArn': queue_arn
    }]
}

resp = s3_client.put_bucket_notification_configuration(
    Bucket=bucket_name,
    NotificationConfiguration=bucket_notifications_configuration
)
resp

# --- UPLOAD FILE ---

for i in range(10):
    file_name = f'test_40{i}.txt'
    open(file_name, 'w').writelines(['hello'])
    s3_client.upload_file(file_name, Bucket=bucket_name, Key=file_name)

# check result
obj = s3_res.Object(bucket_name, file_name)
text = obj.get()['Body'].read()
print(text)

# --- GET MESSAGES ---

def get_key():
    message = sqs_client.receive_message(QueueUrl=queue_url)
    body = message["Messages"][0]["Body"]
    body_dict = json.loads(body)
    return body_dict["Records"][0]["s3"]["object"]["key"]

for i in range(5):
    print(get_key())

# --- CLEAN UP ---

# Empty and delete buckets
bucket = s3_res.Bucket(bucket_name)
bucket.objects.all().delete()
s3_client.delete_bucket(Bucket=bucket_name)

# Delete queue
sqs_client.delete_queue(QueueUrl=queue_url)
