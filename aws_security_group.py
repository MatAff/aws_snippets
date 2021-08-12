
import boto3
import pandas as pd

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')

# permissions
HTTP_PERMISSIONS = [
    {
        # HTTP ingress open to anyone
        'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80,
        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
    },
    {
        # HTTPS ingress open to anyone
        'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443,
        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
    },
    {
        'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
    }
]


def get_security_group_df():
    sgs = ec2_client.describe_security_groups()
    return pd.DataFrame(sgs['SecurityGroups'])


def get_http_security_group(name='http', desc='http'):
    # TODO: update to handle vpc

    # check if exists
    sg_df = get_security_group_df()
    if name in sg_df.GroupName.values:
        return name

    # create security group
    response = ec2_client.create_security_group(
        GroupName=name, 
        Description=desc, 
        TagSpecifications=[{'ResourceType': 'security-group', 'Tags': [{'Key': 'purpose', 'Value': 'http'}]}]
    )

    # associate permissions
    ec2_client.authorize_security_group_ingress(
        GroupName=name,
        IpPermissions=HTTP_PERMISSIONS
    )

    return name


def delete_security_group(name):
    ec2_client.delete_security_group(GroupName=name)
