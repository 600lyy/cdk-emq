import json
import pytest

from aws_cdk import core
from cdk_emq.cdk_emq_stack import CdkEmqStack


def get_template():
    app = core.App()
    CdkEmqStack(app, "cdk-emq")
    return json.dumps(app.synth().get_stack("cdk-emq").template)


def test_sqs_queue_created():
    assert("AWS::SQS::Queue" in get_template())


def test_sns_topic_created():
    assert("AWS::SNS::Topic" in get_template())
