
import json

import boto3
import pandas as pd

# --- S3 ---

# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-examples.html

s3_client = boto3.client('s3')
s3_res = boto3.resource('s3')

# list buckets
buckets = s3_client.list_buckets()
buckets_df = pd.DataFrame(buckets['Buckets'])
buckets_df

# create bucket
bucket_name = 'sample-bucket-afasfsagad'
s3_client.create_bucket(Bucket=bucket_name)

# add a file
with open('sample.txt', 'w') as file:
    file.writelines(['hello world'])
s3_client.upload_file('sample.txt', bucket_name, 'sample')

# list files
objects = s3_client.list_objects(Bucket=bucket_name)
objects_df = pd.DataFrame(objects['Contents'])
objects_df

# read file
obj = s3_res.Object(bucket_name, 'sample')
text = obj.get()['Body'].read()
print(text)

# alter
text = text.upper()
print(text)

# put
obj = s3_res.Object(bucket_name, 'sample')
obj.put(Body=text)

# download a file
s3_client.download_file(bucket_name, 'sample', 'sample.txt')

# delete a file
s3_client.delete_object(Bucket=bucket_name, Key='sample')

# add a bucket policy
# http://awspolicygen.s3.amazonaws.com/policygen.html

read_policy = {
  "Id": "Policy1626479963991",
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Stmt1626479959993",
      "Action": [
        "s3:GetObject"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:s3:::sample-bucket-afasfsagad/*",
      "Principal": "*"
    }
  ]
}

# contert to string and add policy
read_policy = json.dumps(read_policy)
s3_client.put_bucket_policy(Bucket=bucket_name, Policy=read_policy)

noread_policy = {
  "Id": "Policy1626480386835",
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Stmt1626480379271",
      "Action": [
        "s3:GetObject"
      ],
      "Effect": "Deny",
      "Resource": "arn:aws:s3:::sample-bucket-afasfsagad/*",
      "Principal": "*"
    }
  ]
}

# contert to string and add policy
noread_policy = json.dumps(noread_policy)
s3_client.put_bucket_policy(Bucket=bucket_name, Policy=noread_policy)

# delete bucket
sts_client = boto3.client('sts')
account = sts_client.get_caller_identity()['Arn']
s3_client.delete_bucket(Bucket=bucket_name, ExpectedBucketOwner=account)
# this failed, manually deleted from console
