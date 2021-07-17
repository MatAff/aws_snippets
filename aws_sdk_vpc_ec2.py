
import boto3
import pandas as pd

ec2_client = boto3.client('ec2')

# TODO: track create resources and store in json for easy deletion

# --- VPC ---

# list vpc
vpcs = ec2_client.describe_vpcs()
pd.DataFrame(vpcs['Vpcs'])

# create vpc
response = ec2_client.create_vpc(CidrBlock='10.0.0.0/24')
vpc_id = response['Vpc']['VpcId']
print(vpc_id)

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

# TODO: figure out how to make public
# map_public_ip_on_launch

# list internet gateways
igws = ec2_client.describe_internet_gateways()
pd.DataFrame(igws['InternetGateways'])

# --- ACL ---



# --- IGW ---

# create internet gateway
igw = ec2_client.create_internet_gateway()
igw_id = igw['InternetGateway']['InternetGatewayId']
print(igw_id)

# TODO: figure out how to associate igw with vpc

# --- VPG ----

# list vpg
vpgs = ec2_client.describe_vpn_gateways()
pd.DataFrame(vpgs['VpnGateways'])

# create virtual private gateway
vpg = ec2_client.create_vpn_gateway()
print(vpg)

# --- EC2 --- 


# --- ROUTE TABLE ---


# --- SECURITY GROUP ---


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

term = 'subnet'
[e for e in dir(ec2_client) if term in e]
