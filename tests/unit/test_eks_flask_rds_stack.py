import aws_cdk as core
import aws_cdk.assertions as assertions

from eks_flask_rds.eks_flask_rds_stack import EksFlaskRdsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in _stacks/eks_rds.py
def test_sqs_queue_created():
    app = core.App()
    stack = EksFlaskRdsStack(app, "eks-flask-rds")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
