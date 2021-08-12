"""
EC2 Exploration

Spin up a ec2 instance and host a webserver. This is the simplified version
of running the same in an vpc.
"""

import boto3
import pandas as pd

import aws_security_group
import aws_iam

pd.options.display.max_colwidth = 200

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')

# --- SETTINGS ---

purpose = 'aws_exploration'

# --- SECURITY GROUP ---

sg_name = aws_security_group.get_http_security_group()

# --- IAM ---

instance_profile = aws_iam.get_instance_profile()

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
    SecurityGroups=(sg_name, ),
    UserData=user_data,
    IamInstanceProfile={'Name': 'ec2_instance_profile'},
    MinCount=1, 
    MaxCount=1
)
instances

# --- CLEAN UP ---

# delete ec2
ec2_client.terminate_instances(InstanceIds=(instances[0].id,))

# delete key
ec2_client.delete_key_pair(KeyName=key_name)


# user_data = """#!/bin/bash
# touch hello_world.txt
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
# """

# yum install -y httpd24 php72 mysql57-server php72-mysqlnd
# service httpd start
# chkconfig httpd on
# """
