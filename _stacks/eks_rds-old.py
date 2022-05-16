import json
import yaml
import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_ec2
from aws_cdk import aws_rds
from aws_cdk import aws_secretsmanager
from aws_cdk import aws_iam
from aws_cdk import aws_eks


class EksRdsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        stack_name = 'eks_rds'
        db_name = 'mydb'
        db_user = 'mydbuser'
        vpc_cidr = '10.10.0.0/16'
        eks_cidr = '172.11.0.0/24'

        # --------------------------------------------------------------
        # VPC
        #   Three Tire Network
        # --------------------------------------------------------------
        vpc = aws_ec2.Vpc(
            self,
            'Vpc',
            cidr=vpc_cidr,
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                aws_ec2.SubnetConfiguration(
                    name="Front",
                    subnet_type=aws_ec2.SubnetType.PUBLIC,
                    cidr_mask=24),
                aws_ec2.SubnetConfiguration(
                    name="EKS-Application",
                    subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_NAT,
                    cidr_mask=24),
                aws_ec2.SubnetConfiguration(
                    name="DataStore",
                    subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24),
            ],
        )

        # --------------------------------------------------------------
        # EKS Cluster
        #   Owner role for EKS Cluster
        # ----------------------------------------------------------
        # owner_role = aws_iam.Role(
        #     scope=self,
        #     id='EksClusterOwnerRole',
        #     role_name='EksClusterOwnerRole',
        #     assumed_by=aws_iam.AccountRootPrincipal()
        # )

        eks_cluster = aws_eks.Cluster(
            self,
            'EksAppCluster',
            cluster_name='AppCluster',
            # output_cluster_name=True,
            version=aws_eks.KubernetesVersion.V1_21,
            # endpoint_access=aws_eks.EndpointAccess.PUBLIC,
            # masters_role=owner_role,
            default_capacity=1,  # 2
            default_capacity_instance=aws_ec2.InstanceType('t3.small'),
            vpc=vpc,
            # vpc_subnets=_vpc.vpc.private_subnets, # Default: - All public and private subnets
        )

        # --------------------------------------------------------------
        # AddManifestしたい。
        # --------------------------------------------------------------
        eks_cluster.


        # --------------------------------------------------------------
        # RDS Network
        #   RDS Subnet Group
        #   RDS Security Group
        # --------------------------------------------------------------
        # db_subnet_group = aws_rds.SubnetGroup(
        #     self,
        #     'DbSubnetGroup',
        #     vpc=vpc,
        #     subnet_group_name='rds-subnet-group',
        #     description='rds subnet group',
        #     vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED),
        #     # removal_policy=aws_cdk.RemovalPolicy.DESTROY
        # )
        # selection = vpc.select_subnets(
        #     subnet_group_name='EKS-Application',
        #     # subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_NAT,
        # )
        #
        # rds_security_group = aws_ec2.SecurityGroup(
        #     self, 'RdsSecurityGroup', vpc=vpc, security_group_name='RdsMysql')
        # # rds_security_group.add_ingress_rule(
        # #     eks_cluster.cluster_security_group, aws_ec2.Port.tcp(3306))
        # for subnet in selection.subnets:
        #     rds_security_group.add_ingress_rule(
        #         aws_ec2.Peer.ipv4(subnet.ipv4_cidr_block),
        #         aws_ec2.Port.tcp(3306),
        #         'allow rds from EKS application subnets'
        #     )

        # --------------------------------------------------------------
        # Secret for RDS User, Password
        # --------------------------------------------------------------
        # rds_secret = aws_secretsmanager.Secret(
        #     self,
        #     'RdsUserSecret',
        #     generate_secret_string=aws_secretsmanager.SecretStringGenerator(
        #         secret_string_template=json.dumps({'username': db_user}),
        #         generate_string_key='password',
        #         # exclude_punctuation=True,
        #         # include_space=False,
        #     )
        # )

        # --------------------------------------------------------------
        # RDS
        # EKS　Podが利用するRDSをPRIVATE subnetに作成
        # credentials: defaultでdbパスワードが生成され、AWS Secret Managerに登録される
        # allow_default_port_from(cluster)でPodからRDSへの疎通を許可する。
        # --------------------------------------------------------------
        rds_instance = aws_rds.DatabaseInstance(
            self,
            'rds',
            instance_identifier='rds-mysql-for-eks',
            engine=aws_rds.DatabaseInstanceEngine.mysql(
                version=aws_rds.MysqlEngineVersion.VER_5_7_30
            ),
            instance_type=aws_ec2.InstanceType.of(aws_ec2.InstanceClass.BURSTABLE3, aws_ec2.InstanceSize.SMALL),
            # credentials=aws_rds.Credentials.from_secret(rds_secret),
            allocated_storage=5,
            database_name=db_name,
            vpc=vpc,
            vpc_subnets=aws_ec2.SubnetType.PRIVATE_ISOLATED
            # subnet_group=db_subnet_group,
            # security_groups=[rds_security_group],
            # delete_automated_backups=True,
            # removal_policy=aws_cdk.RemovalPolicy.DESTROY
        )
        rds_instance.connections.allow_default_port_from(eks_cluster)

        # --------------------------------------------------------------
        # kubernetes-external-secretsを使用してSecretManagerに格納されたRDSの接続情報を
        # KubernetesのSecretに連携する。
        # PodがAWS Secrets Managerの接続情報をk8sのSecret経由で取得する。
        # k8sサービスアカウントとIAM Roleの連携()
        # --------------------------------------------------------------
        rds_instance.secret.grant_read()








        # aws_cdk.CfnOutput(self, 'DbUserName', export_name='db_user_name', value=db_user)
        # aws_cdk.CfnOutput(self, 'DbName', export_name='db_name', value=db_name)
        # aws_cdk.CfnOutput(self, 'VpcId', export_name='vpc_id', value=vpc.vpc_id)
        # aws_cdk.CfnOutput(self, 'DbHost', export_name='db_host_address', value=db_host.db_instance_endpoint_address)
        # aws_cdk.CfnOutput(self, 'DbSG', export_name='db_security_group', value=rds_security_group.security_group_id)
        # aws_cdk.CfnOutput(self, 'RdsSecretArn', export_name='rds_secret_arn', value=rds_secret.secret_arn)
        # aws_cdk.CfnOutput(self, 'RdsSecretId', export_name='rds_secret_id', value=rds_secret.secret_name)
