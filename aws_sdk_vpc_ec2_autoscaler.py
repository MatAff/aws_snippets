
"""VPC EC2 Webserver

Document to process to set up a VPC, EC2 based webserver with auto scaling
"""

# Reference material: 
# https://gist.github.com/nguyendv/8cfd92fc8ed32ebb78e366f44c2daea6
# https://github.com/miztiik/AWS-Demos/blob/master/How-To/setup-autoscaling-with-boto3/setup-autoscaling-with-boto3

import time

import boto3
import pandas as pd

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')

# --- SETTINGS ---

tags = [
    {'Key': 'purpose', 'Value': 'aws_exploration'},
    {'Key': 'temporary', 'Value': 'true'},
]

# --- VPC ---

# list vpcs
pd.DataFrame(ec2_client.describe_vpcs()['Vpcs'])

# create vpc
vpc = ec2_res.create_vpc(CidrBlock='10.0.0.0/24')
vpc.modify_attribute(EnableDnsSupport={'Value': True})
vpc.modify_attribute(EnableDnsHostnames={'Value': True})
vpc.create_tags(Tags=tags)

print('created vpc')
time.sleep(1.0)

# --- SUBNET ---

# list vpc subnets
subnet_df = pd.DataFrame(ec2_client.describe_subnets()['Subnets'])
subnet_df[subnet_df.VpcId==vpc.id]

# create subnets
subnet_az1_pub = vpc.create_subnet(CidrBlock='10.0.0.16/28', AvailabilityZone='us-east-1a')
subnet_az2_pub = vpc.create_subnet(CidrBlock='10.0.0.32/28', AvailabilityZone='us-east-1b')

print('created subnets')
time.sleep(1.0)

subnet_az1_pub.create_tags(Tags=tags)
subnet_az2_pub.create_tags(Tags=tags)

# --- IGW ---

# list internet gateways
pd.DataFrame(ec2_client.describe_internet_gateways()['InternetGateways'])

# create internet gateway and attach to vpc
igw = ec2_res.create_internet_gateway()
igw.create_tags(Tags=tags)
igw.attach_to_vpc(VpcId=vpc.id)

print('created igw')
time.sleep(1.0)

# --- ROUTE TABLE ---

# list route tables
pd.DataFrame(ec2_client.describe_route_tables()['RouteTables'])

# create route table
route_table = vpc.create_route_table()
route_table.create_tags(Tags=tags)
routes = []
routes.append(route_table.associate_with_subnet(SubnetId=subnet_az1_pub.id))
routes.append(route_table.associate_with_subnet(SubnetId=subnet_az2_pub.id))
int_route = route_table.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=igw.id)

print('created route table')
time.sleep(1.0)

# --- SECURITY GROUP ---

# permissions
HTTP_PERMISSIONS = [
    {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
]

PORT_80_PERMISSIONS = [
    {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
]

# create sec group - public
sg_pub = vpc.create_security_group(GroupName ='http', Description='http')
sg_pub.authorize_ingress(IpPermissions=HTTP_PERMISSIONS)
sg_pub.create_tags(Tags=tags)

# create sec group - elb
sg_elb = vpc.create_security_group(GroupName ='elb', Description='elb')
sg_elb.authorize_ingress(IpPermissions=PORT_80_PERMISSIONS)
sg_elb.create_tags(Tags=tags)

# allow public security group to receive traffic from elb
ec2_client.authorize_security_group_ingress(
    GroupId=sg_pub.id, IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'UserIdGroupPairs': [{'GroupId': sg_elb.id}]}]
)

print('created security group')
time.sleep(1.0)

# --- KEY PAIR ---

# create key pair
key_name = 'my_key'
key_pair = ec2_client.create_key_pair(KeyName=key_name)
with open(key_name, 'w') as file:
    file.write(str(key_pair))

print('created key pair')
time.sleep(1.0)

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

print('found image')
time.sleep(1.0)

# --- EC2 ---

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

user_data = '\n'.join(open('user_data.sh').readlines())

# # list instances
# reservations = ec2_client.describe_instances()['Reservations']
# ec2_df = pd.concat([pd.DataFrame(res['Instances']) for res in reservations])
# ec2_df
# ec2_vpc_df = ec2_df[ec2_df.VpcId == vpc.id]
# ec2_vpc_df

# instances = ec2_res.create_instances(
#     ImageId=ami_image_id,
#     InstanceType='t2.micro', 
#     KeyName=key_name,
#     UserData=user_data,
#     MaxCount=1, 
#     MinCount=1,
#     NetworkInterfaces=[{
#         'SubnetId': subnet_az1_pub.id, 
#         'DeviceIndex': 0, 
#         'AssociatePublicIpAddress': True, 
#         'DeleteOnTermination': True,
#         'Groups': [sg_pub.group_id]
#     }]
# )

# --- AUTO SCALER ---

as_client = boto3.client('autoscaling')

# autoscaler launch configuration
as_launch_config = as_client.create_launch_configuration(
    LaunchConfigurationName='auto_scaling_launch_config',
    ImageId=ami_image_id,
    KeyName=key_name,
    SecurityGroups=[sg_pub.group_id],
    UserData=user_data,
    InstanceType='t2.micro',
    InstanceMonitoring={'Enabled': False },
    EbsOptimized=False,
    AssociatePublicIpAddress=True
)
# as_launch_config.create_tags(Tags=tags)

print('created lauch configuration')
time.sleep(1.0)

# auto scaling group
as_subnets = subnet_az1_pub.id + "," + subnet_az2_pub.id
as_group = as_client.create_auto_scaling_group(
    AutoScalingGroupName='auto_scaling_group',
    LaunchConfigurationName='auto_scaling_launch_config',
    MinSize=1,
    MaxSize=3,
    DesiredCapacity=2,
    DefaultCooldown=120,
    HealthCheckType='EC2',
    HealthCheckGracePeriod=60,
    Tags=tags,
    VPCZoneIdentifier=as_subnets
)

as_client.create_or_update_tags(
    Tags=[{
            'ResourceId': 'auto_scaling_group',
            'ResourceType': 'auto-scaling-group',
            'Key': 'Name',
            'Value': 'aws_exploration',
            'PropagateAtLaunch': True
        }]
)

print('created auto scaler group')
print('long pause')
time.sleep(60.0)

# --- LOAD BALANCER ---

elb_client = boto3.client(service_name="elbv2")

# create a load balancer
lb_response = elb_client.create_load_balancer(
    Name='my-lb',
    Subnets=[subnet_az1_pub.id, subnet_az2_pub.id],
    SecurityGroups=[sg_elb.id],
    Scheme='internet-facing'
)
lb_arn = lb_response['LoadBalancers'][0]['LoadBalancerArn']

# create target-group
tg_response = elb_client.create_target_group(
    Name='my-target-group',
    Protocol='HTTP', # should this be http?
    Port=80,
    VpcId=vpc.id
)
tg_arn = tg_response['TargetGroups'][0]['TargetGroupArn']

# attach to auto scaler
# https://docs.aws.amazon.com/autoscaling/ec2/userguide/attach-load-balancer-asg.html
attach_response = as_client.attach_load_balancer_target_groups(
    AutoScalingGroupName='auto_scaling_group',
    TargetGroupARNs=[tg_arn, ],
)

# register targets

# list instances
reservations = ec2_client.describe_instances()['Reservations']
ec2_df = pd.concat([pd.DataFrame(res['Instances']) for res in reservations])
ec2_df
ec2_vpc_df = ec2_df[ec2_df.VpcId == vpc.id]
ec2_vpc_df

target_ids = ec2_vpc_df.InstanceId.tolist()
target_ids


targets_list = [dict(Id=target_id, Port=80) for target_id in target_ids] 
reg_targets_response = elb_client.register_targets(
    TargetGroupArn=tg_arn, 
    Targets=targets_list
)

# create Listener
create_listener_response = elb_client.create_listener(
    LoadBalancerArn=lb_arn,
    Protocol='HTTP', 
    Port=80,
    DefaultActions=[{
        'Type': 'forward',
        'TargetGroupArn': tg_arn
    }]
)

print('created load balancer')
time.sleep(1.0)


assert False

# --- CLEAN UP ---

# delete auto scaler
as_client.delete_auto_scaling_group(
    AutoScalingGroupName='auto_scaling_group',
    ForceDelete=True,
)

print('deleted auto scaler')
time.sleep(1.0)

# delete launch configuration
as_client.delete_launch_configuration(
    LaunchConfigurationName='auto_scaling_launch_config'
)

print('deleted launch configuration')
time.sleep(1.0)

# delete load balander
elb_client.delete_load_balancer(LoadBalancerArn=lb_arn)

print('deleted load balancer')
time.sleep(5.0)

# delete target group
elb_client.delete_target_group(TargetGroupArn=tg_arn)

print('deleted target group')
time.sleep(1.0)

# get instances
reservations = ec2_client.describe_instances()['Reservations']
ec2_df = pd.concat([pd.DataFrame(res['Instances']) for res in reservations])
ec2_vpc_df = ec2_df[ec2_df.VpcId == vpc.id]
ec2_vpc_df

# terminate instances
ec2_client.terminate_instances(InstanceIds=ec2_vpc_df.InstanceId.tolist())

print('initialized terminating instances')
print('long pause')
time.sleep(20.0)

# # delete ec2
# ec2_client.terminate_instances(InstanceIds=(instances[0].id,))
# instances[0].wait_until_terminated()

# delete key
ec2_client.delete_key_pair(KeyName=key_name)

print('deleted key')
print('long pause')
time.sleep(60.0)

# delete security group
ec2_client.delete_security_group(GroupId=sg_pub.id)
ec2_client.delete_security_group(GroupId=sg_elb.id)

print('deleted security group')
time.sleep(1.0)

# delete subnet
ec2_client.delete_subnet(SubnetId=subnet_az1_pub.id)
ec2_client.delete_subnet(SubnetId=subnet_az2_pub.id)

print('deleted subnet')
time.sleep(1.0)

# # delete vpc associated subnets
# for subnet_id in vpc_subnets_df.SubnetId.values:
#     print(subnet_id)
#     ec2_client.delete_subnet(SubnetId=subnet_id)

# delete route table
ec2_client.delete_route_table(RouteTableId=route_table.id)

print('deleted route table')
time.sleep(1.0)

# detach and delete igw
vpc.detach_internet_gateway(InternetGatewayId=igw.id)
ec2_client.delete_internet_gateway(InternetGatewayId=igw.id)

print('deleted igw')
time.sleep(1.0)

# delete vpc
ec2_client.delete_vpc(VpcId=vpc.id) # delete vpc

print('deleted vpc')
time.sleep(1.0)


print('finished')
