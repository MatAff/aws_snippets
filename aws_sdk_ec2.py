"""
EC2 Exploration

Spin up a ec2 instance and host a webserver. This is the simplified version
of running the same in an vpc.
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

# --- IAM ---

# --- IAM ---
iam_res = boto3.resource('iam')
iam_client = boto3.client('iam')

# create instance profile with tag
response = client.create_instance_profile(
    InstanceProfileName='ec2_instance_profile',
    Path='string',
    Tags=[
        {
            'Key': 'purpose',
            'Value': purpose
        },
    ]
)


# add role to instance profile



# --- SECURITY GROUP ---

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')

# list
sgs = ec2_client.describe_security_groups()
sgs_df = pd.DataFrame(sgs['SecurityGroups'])
sgs_df

# create security group
sg_name = "http"
sg_desc = "http"
tag_spec=[{'ResourceType': 'security-group', 'Tags': [{'Key': 'purpose', 'Value': purpose}]}]
sg_response = ec2_client.create_security_group(GroupName=sg_name, Description=sg_desc, TagSpecifications=tag_spec)

# track created resources
resource_dict['resources'].append(sg_response)
json.dump(resource_dict, open(path_resources, 'w'), indent=4)

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

# # delete security group
# ec2_client.delete_security_group(GroupName=sg_name)

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

# https://docs.aws.amazon.com/code-samples/latest/catalog/python-ec2-ec2_basics-ec2_basics_demo.py.html
# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html

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
instance

# # terminate instance
# ec2_client.terminate_instances(InstanceIds=(instance.id,))

# # delete key
# ec2_client.delete_key_pair(KeyName=key_name)

# --- CLEAN UP ---

# delete ec2
ec2_client.terminate_instances(InstanceIds=(instance.id,))

# delete security group
ec2_client.delete_security_group(GroupName=sg_name)

# delete key
ec2_client.delete_key_pair(KeyName=key_name)

# #!/bin/bash
# yum update -y
# amazon-linux-extras install -y lamp-mariadb10.2-php7.2 php7.2
# yum install -y httpd mariadb-server
# systemctl start httpd
# systemctl enable httpd
# usermod -a -G apache ec2-user
# chown -R ec2-user:apache /var/www
# chmod 2775 /var/www
# find /var/www -type d -exec chmod 2775 {} \;
# find /var/www -type f -exec chmod 0664 {} \;
# echo "<?php phpinfo(); ?>" > /var/www/html/phpinfo.php
