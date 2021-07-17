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
