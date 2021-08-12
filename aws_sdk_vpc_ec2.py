
"""VPC EC2 Webserver

Document to process to set up a VPC, EC2 based webserver.
"""

# Reference material: https://gist.github.com/nguyendv/8cfd92fc8ed32ebb78e366f44c2daea6

import boto3
import pandas as pd

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')

# --- SETTINGS ---

purpose = 'aws_exploration'

# --- VPC ---

# list vpc
vpcs = ec2_client.describe_vpcs()
vpcs_df = pd.DataFrame(vpcs['Vpcs'])
vpcs_df

# create vpc
vpc = ec2_res.create_vpc(
    CidrBlock='10.0.0.0/24', 
    TagSpecifications=[{'ResourceType': 'vpc', 'Tags': [{'Key': 'purpose', 'Value': purpose}]}]
)

# --- IGW ---

# list internet gateways
igws = ec2_client.describe_internet_gateways()
igws_df = pd.DataFrame(igws['InternetGateways'])
igws_df

# create internet gateway and attach to vpc
igw = ec2_res.create_internet_gateway(TagSpecifications=[{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'purpose', 'Value': purpose}]}])
igw.attach_to_vpc(VpcId=vpc.id)

# --- ROUTE TABLE ---

# list route tables
route_tables = ec2_client.describe_route_tables()
route_table_df = pd.DataFrame(route_tables['RouteTables'])
route_table_df

# create route table and route
route_table = vpc.create_route_table()
route = route_table.create_route(
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=igw.id,
    # TagSpecifications=[{'ResourceType': 'route-table', 'Tags': [{'Key': 'purpose', 'Value': purpose}]}]
)

# --- SUBNET ---

# list subnets
subnets = ec2_client.describe_subnets()
subnet_df = pd.DataFrame(subnets['Subnets'])
subnet_df

# vpc subnets
vpc_subnets_df = subnet_df[subnet_df.VpcId==vpc.id]
vpc_subnets_df

# create public subnet
subnet = ec2_res.create_subnet(
    VpcId=vpc.id,
    CidrBlock='10.0.0.0/28',
    AvailabilityZone='us-east-1a',
    TagSpecifications=[{'ResourceType': 'subnet', 'Tags': [{'Key': 'purpose', 'Value': purpose}]}]
)

# associate the route table with the subnet
route_table.associate_with_subnet(SubnetId=subnet.id)

# --- SECURITY GROUP ---

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

# Create sec group
sg = ec2_res.create_security_group(
    GroupName ='http',
    Description='http',
    VpcId=vpc.id,
    TagSpecifications=[{'ResourceType': 'security-group', 'Tags': [{'Key': 'purpose', 'Value': 'http'}]}]
)
sg.authorize_ingress(IpPermissions=HTTP_PERMISSIONS)

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

# create key pair
key_name = 'my_key'
key_pair = ec2_client.create_key_pair(KeyName=key_name)
with open(key_name, 'w') as file:
    file.write(str(key_pair))

# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-lamp-amazon-linux-2.html

user_data = """#!/bin/bash
touch hello_world.txt
sudo yum update -y
sudo amazon-linux-extras install -y lamp-mariadb10.2-php7.2 php7.2
sudo yum install -y httpd mariadb-server
sudo systemctl start httpd
sudo systemctl enable httpd
sudo systemctl is-enabled httpd
"""

instances = ec2_res.create_instances(
    ImageId=ami_image_id,
    InstanceType='t2.micro', 
    KeyName=key_name,
    UserData=user_data,
    MaxCount=1, 
    MinCount=1,
    NetworkInterfaces=[{
        'SubnetId': subnet.id, 
        'DeviceIndex': 0, 
        'AssociatePublicIpAddress': True, 
        'Groups': [sg.group_id]
    }]
)
instances[0].wait_until_running()
print(instances[0].id)

# --- CLEAN UP ---

# delete ec2
ec2_client.terminate_instances(InstanceIds=(instances[0].id,))
instances[0].wait_until_terminated()

# delete key
ec2_client.delete_key_pair(KeyName=key_name)

# delete security group
ec2_client.delete_security_group(GroupId=sg.id)

# delete subnet
ec2_client.delete_subnet(SubnetId=subnet.id)

# # delete vpc associated subnets
# for subnet_id in vpc_subnets_df.SubnetId.values:
#     print(subnet_id)
#     ec2_client.delete_subnet(SubnetId=subnet_id)

# delete route table
ec2_client.delete_route_table(RouteTableId=route_table.id)

# detach and delete igw
vpc.detach_internet_gateway(InternetGatewayId=igw.id)
ec2_client.delete_internet_gateway(InternetGatewayId=igw.id)

# delete vpc
ec2_client.delete_vpc(VpcId=vpc.id) # delete vpc

print('finished')
