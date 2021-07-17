! python3 -m pip install boto3

import json
import os
from pprint import pprint

import boto3
import pandas as pd

# --- IAM ---
iam_res = boto3.resource('iam')
iam_client = boto3.client('iam')

# --- POLICIES ---

# policies
policies = iam_client.list_policies(MaxItems=1000)
policies_df = pd.DataFrame(policies['Policies'])

# explore policies
policies_df[policies_df.PolicyName.str.contains('S3')]


def lookup_policy_arm(policy_name):
    policies = iam_client.list_policies(MaxItems=1000)
    policies_df = pd.DataFrame(policies['Policies'])
    arn = policies_df[policies_df.PolicyName==policy_name].Arn.iloc[0]
    return arn


# --- GROUPS ---

# groups
groups = iam_client.list_groups()
display(pd.DataFrame(groups['Groups']))

# create group
response = iam_client.create_group(GroupName='EC2-Support')
pprint(response)
EC2_support_group = iam_res.Group('EC2-Support')
EC2_support_group.attach_policy(PolicyArn=lookup_policy_arm('AmazonEC2ReadOnlyAccess'))

# create group
iam_client.create_group(GroupName='S3-Support')
S3_support_group = iam_res.Group('S3-Support')
S3_support_group.attach_policy(PolicyArn=lookup_policy_arm('AmazonS3ReadOnlyAccess'))

# create group
iam_client.create_group(GroupName='EC2-Admin')
EC2_admin_group = iam_res.Group('EC2-Admin')

EC2_admin_group.attach_policy(Policy={})

dir(EC2_admin_group)


# --- USERS ---

# users
users = iam_client.list_users() 
display(pd.DataFrame(users['Users']))

# create user
response = iam_client.create_user(UserName='user_1')
pprint(response)

# explore user
user_1 = iam_res.User('user_1')
user_1.groups

# additional users created
response = iam_client.create_user(UserName='user_2')
response = iam_client.create_user(UserName='user_3')

# --- ROLES ---

# roles
roles = iam_client.list_roles()
display(pd.DataFrame(roles['Roles']))

# --- EC2 ---

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')



ec2_res.instances

dir(ec2_res)

[e for e in dir(ec2_client) if 'list' in e]

# vpc (across az)
# igw
# vgw
# nat
# private subnet
# public subnet
# ec2
# db
# acl
# security group

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
    file.writelines([])
s3_client.upload_file('sample.txt', bucket_name, 'sample')

# list files
objects = s3_client.list_objects(Bucket=bucket_name)
objects_df = pd.DataFrame(objects['Contents'])
objects_df

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

