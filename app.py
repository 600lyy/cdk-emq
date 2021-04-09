#!/usr/bin/env python3

from aws_cdk import core

from emq_stack.emq_full_stack import EmqFullStack
from emq_stack import AWS_ENV


app = core.App()
emq_stack = EmqFullStack(app, "emq-full-stack", env=AWS_ENV)

app.synth()