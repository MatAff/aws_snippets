
"""Document Common AWS SDK Operations

This script is used to document common AWS operations, 
as well as provide a working example of setting up an
environment.
"""

import json
import os

import boto3
import pandas as pd

pd.options.display.max_colwidth = 200

# --- SETTINGS ---

path_resources = './resources.json'

purpose = 'aws_exploration'

# --- RESOURCE TRACKING ---

if os.path.exists(path_resources):
    resource_dict = json.load(open(path_resources))
else:
    resource_dict = {'resources': []}

# --- VPC ---

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')

# list vpc
vpcs = ec2_client.describe_vpcs()
vpcs_df = pd.DataFrame(vpcs['Vpcs'])
vpcs_df

# create vpc
tag_spec=[{'ResourceType': 'vpc', 'Tags': [{'Key': 'purpose', 'Value': purpose}]}]
response = ec2_client.create_vpc(
    CidrBlock='10.0.0.0/24', 
    TagSpecifications=tag_spec
)

# track created resources
resource_dict['resources'].append(response)
json.dump(resource_dict, open(path_resources, 'w'), indent=4)

# vpc id
vpc_id = response['Vpc']['VpcId']
print(vpc_id)

# instanciate by id
vpc = ec2_res.Vpc(vpc_id)

# # delete vpc
# ec2_client.delete_vpc(VpcId=vpc_id) # delete vpc

# --- IGW ---

# list internet gateways
igws = ec2_client.describe_internet_gateways()
igws_df = pd.DataFrame(igws['InternetGateways'])
igws_df

# # get existing igw
# igw_id = igws_df.InternetGatewayId.iloc[0]
# print(igw_id)

# create internet gateway
tag_spec=[{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'purpose', 'Value': purpose}]}]
igw_response = ec2_client.create_internet_gateway(TagSpecifications=tag_spec)
igw_id = igw_response['InternetGateway']['InternetGatewayId']
print(igw_id)

# track created resources
resource_dict['resources'].append(igw_response)
json.dump(resource_dict, open(path_resources, 'w'), indent=4)

# instanciate by id
igw = ec2_res.InternetGateway(igw_id)

# attach to vpc
igw.attach_to_vpc(VpcId=vpc_id)

# # detach and delete igw
# vpc.detach_internet_gateway(InternetGatewayId=igw_id)
# ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)

# --- SUBNET ---

# TODO: figure out how to make public
# map_public_ip_on_launch


# list subnets
subnets = ec2_client.describe_subnets()
subnet_df = pd.DataFrame(subnets['Subnets'])
vpc_subnets_df = subnet_df[subnet_df.VpcId==vpc_id]
vpc_subnets_df

# create public subnets
subnet_response = ec2_client.create_subnet(
    VpcId=vpc_id,
    CidrBlock='10.0.0.0/28',
    AvailabilityZone='us-east-1a'
)
subnet_id = subnet_response['Subnet']['SubnetId']
print(subnet_id)

# track created resources
resource_dict['resources'].append(subnet_response)
json.dump(resource_dict, open(path_resources, 'w'), indent=4)

# instanciate by id
subnet = ec2_res.InternetGateway(subnet_id)

# # delete
# ec2_client.delete_subnet(SubnetId=subnet_id)

# --- CLEAN UP ---

# TODO: get vpc_subnets_df

# delete vpc associated subnets
for subnet_id in vpc_subnets_df.SubnetId.values:
    print(subnet_id)
    ec2_client.delete_subnet(SubnetId=subnet_id)

# detach and delete igw
vpc.detach_internet_gateway(InternetGatewayId=igw_id)
ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)

# delete vpc
ec2_client.delete_vpc(VpcId=vpc_id) # delete vpc

assert False

# --- SUBNET ---

# list subnets
subnets = ec2_client.describe_subnets()
subnet_df = pd.DataFrame(subnets['Subnets'])
vpc_subnets_df = subnet_df[subnet_df.VpcId==vpc_id]
vpc_subnets_df

# create public subnets - a
ec2_client.create_subnet(
    VpcId=vpc_id,
    CidrBlock='10.0.0.0/28',
    AvailabilityZone='us-east-1a'
)

# create public subnets - b
ec2_client.create_subnet(
    VpcId=vpc_id,
    CidrBlock='10.0.0.16/28',
    AvailabilityZone='us-east-1b'
)

# create private subnets - c
ec2_client.create_subnet(
    VpcId=vpc_id,
    CidrBlock='10.0.0.32/28',
    AvailabilityZone='us-east-1a'
)

# create private subnets - d
ec2_client.create_subnet(
    VpcId=vpc_id,
    CidrBlock='10.0.0.48/28',
    AvailabilityZone='us-east-1b'
)


# --- SECURITY GROUP ---

# list
sgs = ec2_client.describe_security_groups()
sgs_df = pd.DataFrame(sgs['SecurityGroups'])
sgs_df

sg_name = "http"
sg_desc = "http"
sg_http = ec2_client.create_security_group(GroupName=sg_name, Description=sg_desc)

# permissions
ip_permissions = [
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
ec2_client.authorize_security_group_ingress(
    GroupName=sg_name,
    IpPermissions=ip_permissions
)

# delete security group
ec2_client.delete_security_group(GroupName=sg_name)

# --- SSM --

ssm_client = boto3.client('ssm')

ami_params = ssm_client.get_parameters_by_path(Path='/aws/service/ami-amazon-linux-latest')
ami_df = pd.DataFrame(ami_params['Parameters'])

# subset
amzn2_amis = [ap for ap in ami_params['Parameters'] if
                all(query in ap['Name'] for query
                    in ('amzn2', 'x86_64', 'gp2'))]

# select first one
ami_image_id = amzn2_amis[0]['Value']
print(ami_image_id)

# --- EC2 ---

https://docs.aws.amazon.com/code-samples/latest/catalog/python-ec2-ec2_basics-ec2_basics_demo.py.html

# create key pair
key_name = 'my_key'
key_pair = ec2_client.create_key_pair(KeyName=key_name)
with open(key_name, 'w') as file:
    file.write(str(key_pair))

# ec2 settings
image_id = ami_image_id
instance_type = 't2.micro'
key_name = key_name
user_data = """
touch test.txt
"""

# create instance
instance_params = {
    'ImageId': image_id,
    'InstanceType': instance_type,
    'KeyName': key_name,
    'SecurityGroups': (sg_name, ),
    'UserData': user_data,
}
instance = ec2_res.create_instances(**instance_params, MinCount=1, MaxCount=1)[0]

# terminate instance
ec2_client.terminate_instances(InstanceIds=(instance.id,))

# delete key
ec2_client.delete_key_pair(KeyName=key_name)

# --- ACL ---



# --- VPG ----

# list vpg
vpgs = ec2_client.describe_vpn_gateways()
pd.DataFrame(vpgs['VpnGateways'])

# create virtual private gateway
vpg = ec2_client.create_vpn_gateway()
print(vpg)

# --- ROUTE TABLE ---



# --- CLEAN UP ---

# delete igw
ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)

# delete vpg


# delete vpc associated ec2


# delete vpc associated subnets
for subnet_id in vpc_subnets_df.SubnetId.values:
    print(subnet_id)
    ec2_client.delete_subnet(SubnetId=subnet_id)

# delete vpc
ec2_client.delete_vpc(VpcId=vpc_id)

# --- SUPPORT ---

term = 'delet'
[e for e in dir(ec2_client) if term in e]
