import os
from aws_cdk import core


# Define stack env to inherit account and region from AWS CLI
ACCOUNT = os.environ.get('EMQ_ACCOUNT', os.environ["CDK_DEFAULT_ACCOUNT"])
REGION = os.environ.get('EMQ_REGION', os.environ["CDK_DEFAULT_REGION"])
AWS_ENV = core.Environment(account=ACCOUNT, region=REGION)