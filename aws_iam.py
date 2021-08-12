
import json

import boto3
import pandas as pd

iam_client = boto3.client('iam')

# create assume role policy document
EC2_ASSUME_ROLE = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
        "Effect": "Allow",
        "Principal": {
            "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
        }
    ]
})


def get_instance_profile(
    profile='ec2_instance_profile',
    role='ec2_full_access_role', 
    policy='AmazonEC2FullAccess'
):

    profiles = iam_client.list_instance_profiles()
    profile_df = pd.DataFrame(profiles['InstanceProfiles'])
    if profile in profile_df.InstanceProfileName.values:
        return profile 

    # create role
    iam_client.create_role(
        RoleName=role,
        AssumeRolePolicyDocument=EC2_ASSUME_ROLE,
        Description=policy,
        MaxSessionDuration=3600,
        Tags=[{'Key': 'purpose', 'Value': policy},]
    )

    # attach policy
    policies = iam_client.list_policies(MaxItems=1000)
    policies_df = pd.DataFrame(policies['Policies'])
    policy_arn = policies_df[policies_df.PolicyName==policy].Arn.iloc[0]
    iam_client.attach_role_policy(
        RoleName=role, 
        PolicyArn=policy_arn
    )

    # create instance profile
    iam_client.create_instance_profile(
        InstanceProfileName='ec2_instance_profile',
        Tags=[{'Key': 'purpose', 'Value': policy},]
    )

    # attach role to instance profile
    iam_client.add_role_to_instance_profile(
        InstanceProfileName=profile,
        RoleName=role
    )

    return profile


def remove_role(profile, role):
    iam_client.remove_role_from_instance_profile(
        InstanceProfileName=profile,
        RoleName=role
    )


def detach_policy(role, policy):
    iam_client.detach_role_policy(
        RoleName=role, 
        PolicyArn=policy
    )


def delete_instance_profile(name):
    # TODO: update to auto remove roles
    iam_client.delete_instance_profile(InstanceProfileName=name)


def delete_role(name):
    # TODO: update to auto detach policies
    iam_client.delete_role(RoleName=name)
