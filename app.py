#!/usr/bin/env python3
import os
import aws_cdk as cdk
# from eks_rds.eks_flask_rds_stack import EksFlaskRdsStack
from _stacks.eks_rds import EksRdsStack

env = cdk.Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

app = cdk.App()
EksRdsStack(app, "EksFlaskRdsStack", env=env)

app.synth()
