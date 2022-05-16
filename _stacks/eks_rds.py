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
from aws_cdk import aws_lambda
from aws_cdk import CustomResource
from iam_policy.elb_policy import aws_load_balancer_controller_iam_policy_statements
from manifests.manifest import ingress_manifest
from manifests.manifest import namespace_manifest
from manifests.manifest import deployment_manifest
from manifests.manifest import service_manifest
from manifests.manifest import create_external_secret_manifest
from manifests.manifest import name_space


class EksRdsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # stack_name = 'eks_rds'
        db_name = 'mysqldb'
        # db_user = 'mydbuser'
        vpc_cidr = '10.10.0.0/16'
        # eks_cidr = '172.11.0.0/24'

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
        cluster = aws_eks.Cluster(
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
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        # アプリケーションのAddManifestしたい。
        #  Service & Deployment
        #
        # xxxxxxxx  NodeがECRにアクセス権限を持っているか？ xxxxxxxxxx
        # xxxxxxxx  NodeがECRにアクセス権限を持っているか？ xxxxxxxxxx
        # xxxxxxxx  NodeがECRにアクセス権限を持っているか？ xxxxxxxxxx
        # xxxxxxxx  NodeがECRにアクセス権限を持っているか？ xxxxxxxxxx
        # xxxxxxxx  NodeがECRにアクセス権限を持っているか？ xxxxxxxxxx
        #
        #
        #
        #
        #
        #
        #
        #
        # --------------------------------------------------------------
        self._namespace = cluster.add_manifest('namespace', namespace_manifest)

        self._deployment = cluster.add_manifest('Deployment', deployment_manifest)
        self._deployment.node.add_dependency(self._namespace)

        self._service = cluster.add_manifest('Service', service_manifest)
        self._service.node.add_dependency(self._deployment)


        # --------------------------------------------------------------
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        # RDS
        # EKS　Podが利用するRDSをPRIVATE subnetに作成
        # credentials: defaultでdbパスワードが生成され、AWS Secret Managerに登録される
        # allow_default_port_from(cluster)でPodからRDSへの疎通を許可する。
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
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
        rds_instance.connections.allow_default_port_from(cluster)

        # --------------------------------------------------------------
        # kubernetes-external-secrets
        #   kubernetes-external-secretsを使用してSecretManagerに格納されたRDS
        #   の接続情報をKubernetesのSecretに連携する。
        #   PodがAWS Secrets Managerの接続情報をk8sのSecret経由で取得する。
        #
        #  - RDSが作成したAWS Secrets Managerの読み取り権限をService Accountに付加
        # 　　k8s Service AccountにAWS Secrets Manager(rds_instance.secret)へのアクセス許可
        # --------------------------------------------------------------
        # cluster_service_account = cluster.serviceAccount(
        flask_service_account = cluster.add_service_account(
            'kubernetes-external-secrets',
            name='kubernetes-external-secrets',
            # namespace='kube-system'
            namespace=name_space
        )
        # IRSAにAWS Secrets Managerへのアクセス権を与える
        external_secrets_policy_statement = {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetResourcePolicy",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecretVersionIds"
            ],
            "Resource": [
                "*"
            ]
        }
        flask_service_account.add_to_principal_policy(
            aws_iam.PolicyStatement.from_json(external_secrets_policy_statement)
        )

        # これ本当に必要？
        # kubernetes-external-secretsのサービスアカウントに接続情報の読み取りを許可
        rds_instance.secret.grant_read(flask_service_account)

        # Deploy kubernetes-external-secrets from Helm Chart
        external_secret_helm_chart = cluster.add_helm_chart(
            'helm-external-secrets',
            chart='kubernetes-external-secrets',
            # version='8.2.2',
            repository='https://external-secrets.github.io/kubernetes-external-secrets/',
            # namespace='kube-system',
            namespace=name_space,
            values={
                'env': {
                    'AWS_REGION': self.region
                },
                'serviceAccount': {
                    'name': flask_service_account.service_account_name,
                    'create': False
                },
                'securityContext': {
                    'fsGroup': 65534
                }
            }
        )
        # --------------------------------------------------------------
        # EKS ClusterにKubernetes External Secretをマニフェストで追加
        # 方法1. eks_cluster.add_manifest()
        # 方法2. aws_eks.KubernetesManifest()
        # 本当はmanifestはいらないんじゃないの？Helmだけで可能なんじゃないの？
        # 以下ではrds_instanceを指定してるが、HelmChartにrds_instanceを指定してあげればいいんじゃないの？
        # https://artifacthub.io/packages/helm/trozz/kubernetes-external-secrets
        # https://artifacthub.io/packages/helm/trozz/kubernetes-external-secrets#add-a-secret
        # kubernetes-external-secretsの使い方がArtifact Hun(↑)に記載されている。
        # AWS KMSにSecretを登録するには以下のマニフェストを追加する。
        # --------------------------------------------------------------
        rds_external_secret = cluster.add_manifest(
            'KubernetesExternalSecret',
            create_external_secret_manifest(rds_instance)
        )
        # このマニフェストがkubernetes-external-secretsのインストール後に実行されるよう依存関係を明示
        rds_external_secret.node.add_dependency(external_secret_helm_chart)

        # --------------------------------------------------------------
        # Custom Resource(Lambda Function)でDBのInitializeを行う
        # PyMySQLのLambda Layerを使う
        # --------------------------------------------------------------
        pymysql_layer = aws_lambda.LayerVersion.from_layer_version_attributes(
            self,
            'PyMySqlLayer',
            layer_version_arn='arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-python38-PyMySQL:4'
        )

        db_initialize_func = aws_lambda.Function(
            self,
            'InitializeRds',
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            handler='lambda_function.handler',
            code=aws_lambda.Code.from_asset('./lambda/initialize_db'),
            vpc=vpc,
            layers=[pymysql_layer],
            environment={
                'DB_SECRET_MANAGER_ARN': rds_instance.secret.secret_arn,
            }
        )
        # Custom Resource
        provider = aws_cdk.custom_resources.Provider(
            self,
            'DbInitializeProvider',
            on_event_handler=db_initialize_func,
            log_retention=aws_cdk.aws_logs.RetentionDays.ONE_DAY,
            vpc=vpc
        )
        CustomResource(
            self,
            'CustomResourceDbInitializer',
            service_token=provider.service_token
        )
        # もしかしてPrivate_ISOLATEDにはアクセスできないかも
        db_initialize_func.connections.allow_to(rds_instance, aws_ec2.Port.tcp(3306))
        rds_instance.secret.grant_read(db_initialize_func)
        rds_instance.grant_connect(db_initialize_func)


        # --------------------------------------------------------------
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        # 　　ALB用　Service Account
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        # --------------------------------------------------------------
        # Service Account for ALB
        # _flask_service_account = cluster.add_service_account(
        #     'aws-load-balancer-controller',
        #     name='kubernetes-external-secrets',
        #     # namespace='kube-system'
        #     namespace=self._namespace
        # )
        # Service AccountにELB Policyを与える
        # for statement in aws_load_balancer_controller_iam_policy['Statement']:
        for statement in aws_load_balancer_controller_iam_policy_statements:
            flask_service_account.add_to_principal_policy(statement)
            # flask_service_account.add_to_principal_policy(aws_iam.PolicyStatement(statement))

        alb_controller_helm_chart = cluster.add_helm_chart(
            'helm-alb-controller',
            chart='aws-load-balancer-controller',
            # namespace='kube-system',
            namespace=name_space,
            repository='https://aws.github.io/eks-charts',
            values={
                'clusterName': cluster.cluster_name,
                'ServiceAccount': {
                    'create': False,
                    'name': flask_service_account.service_account_name,
                }
            }
        )

        alb_ingress = cluster.add_manifest(
            'music-flask-ingress',
            ingress_manifest
        )
        # manifestがhelm chartインストール後に実行されるよう依存関係を明示
        alb_ingress.node.add_dependency(alb_controller_helm_chart)
