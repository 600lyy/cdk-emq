#!/usr/bin/env python3

from aws_cdk import core

from emq_stack.cdk_vpc_stack import CdkVpcStack
from emq_stack.cdk_ec2_stack import CdkEc2Stack
from emq_stack import AWS_ENV


app = core.App()
vpc_stack = CdkVpcStack(app, "emq-vpc", env=AWS_ENV)
ec2_stack = CdkEc2Stack(app, "emq-ec2", vpc=vpc_stack.vpc, env=AWS_ENV)

app.synth()