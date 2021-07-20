
import boto3
import pandas as pd

pd.options.display.max_colwidth = 200

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')

# TODO: track create resources and store in json for easy deletion

# --- VPC ---

# list vpc
vpcs = ec2_client.describe_vpcs()
vpcs_df = pd.DataFrame(vpcs['Vpcs'])
vpcs_df

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


# --- IGW ---

# list internet gateways
igws = ec2_client.describe_internet_gateways()
igws_df = pd.DataFrame(igws['InternetGateways'])
igws_df

# get existing igw
igw_id = igws_df.InternetGatewayId.iloc[0]
print(igw_id)

# create internet gateway
igw = ec2_client.create_internet_gateway()
igw_id = igw['InternetGateway']['InternetGatewayId']
print(igw_id)

# instanciate by id
igw = ec2_res.InternetGateway(igw_id)

# attach to vpc
igw.attach_to_vpc(VpcId=vpc_id)

# delete igw
# ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)

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
