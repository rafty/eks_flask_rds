name = 'hello-flask'
name_space = f'{name}-app'
deployment_name = f'{name}-deployment'
service_name = f'{name}-service'
ingress_name = f'{name}-ingress'
# app_label = {'app': name}
app_label = {
    'app': f'{name}-app-label'
}

namespace_manifest = {
    'apiVersion': 'av1',
    'kind': 'Namespace',
    'metadata': {
        'name': name_space,
        'labels': app_label
    },
}

deployment_manifest = {
    'apiVersion': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {
        'namespace': name_space,
        'name': deployment_name,
        'labels': app_label
    },
    'spec': {
        'replicas': 1,
        'revisionHistoryLimit': 3,
        'selector': {'matchLabels': app_label},
        'template': {
            'metadata': {'labels': app_label},
            'spec': {
                'containers': [
                    {
                        'name': name,




                        # 'image': f'hogehoge/{name}:1.5',  # ecrから取得
                        # tagを修正
                        'image': 'XXXXXXXXXXXX.dkr.ecr.ap-northeast-1.amazonaws.com/eks-test-app:target1',
                        'ports': [
                            {
                                # 'name': 'http',
                                'containerPort': 8080
                            }
                        ],
                        'env': [
                            {
                                'name': 'database_connection_host',
                                'valueFrom': {
                                    'secretKeyRef': {
                                        'name': 'flask-database-secret',
                                        'key': 'host'
                                    }
                                }
                            },
                            {
                                'name': 'database_connection_user',
                                'valueFrom': {
                                    'secretKeyRef': {
                                        'name': 'flask-database-secret',
                                        'key': 'username'
                                    }
                                }
                            },
                            {
                                'name': 'database_connection_password',
                                'valueFrom': {
                                    'secretKeyRef': {
                                        'name': 'flask-database-secret',
                                        'key': 'password'
                                    }
                                }
                            },
                            {
                                'name': 'database_connection_database_name',
                                'valueFrom': {
                                    'secretKeyRef': {
                                        'name': 'flask-database-secret',
                                        'key': 'dbname'
                                    }
                                }
                            },
                        ],
                        'livenessProbe': {
                            'tcpSocket': {
                                'port': 2368
                            },
                            'initialDelaySeconds': 30,
                            'periodSeconds': 10
                        },
                        'resources': {
                            'requests': {
                                'memory': '1Gi',
                                'cpu': '1'
                            },
                            'limits': {
                                'memory': '1Gi',
                                'cpu': '1'
                            }
                        }
                    }
                ]
            }
        }
    }
}

service_manifest = {
    'apiVersion': 'v1',
    'kind': 'Service',
    'metadata': {
        'namespace': name_space,
        'name': service_name,
        'labels': app_label
    },
    'spec': {
        'selector': app_label,
        'type': 'NodePort',  # 注意 ALB経由はNodePort
        'ports': [
            {
                'protocol': 'TCP',
                'port': 80,
                'target_port': 8080
            }
        ],
    }
}

ingress_manifest = {
    'apiVersion': 'networking.k8s.io/v1',
    'kind': 'Ingress',
    'metadata': {
        'namespace': name_space,
        'name': ingress_name,
    },
    'spec': {
        'rules': [
            {
                'http': {
                    'paths': [
                        {
                            'pathType': 'Prefix',
                            'path': '/music',
                            'backend': {
                                'service': {
                                    'name': service_name,
                                    'port': {
                                        'number': 80
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        ]
    }
}

# ingress_manifest = {
#     'apiVersion': 'extensions/v1beta1',
#     'kind': 'Ingress',
#     'metadata': {
#         'name': f'ingress-{name}',
#         'namespace': name_space,
#         'labels': app_label,
#         'annotations': {
#             'kubernetes.io/ingress.class': 'alb',
#             'alb.ingress.kubernetes.io/scheme': 'internet-facing'
#         }
#     },
#     'spec': {
#         'rules': [
#             {
#                 'http': {
#                     'paths': [
#                         {
#                             'path': '/*',
#                             'backend': {
#                                 'serviceName': service_name,
#                                 'servicePort': 80
#                             }
#                         }
#                     ]
#                 }
#             },
#         ]
#     },
#     # 'starus': {
#     #     'loadBalancer': {????}
#     # }
# }


def create_external_secret_manifest(rds_instance):
    external_secret_manifest = {
        'apiVersion': 'kubernetes-client.io/v1',
        'kind': 'ExternalSecret',
        'metadata': {
            'name': 'flask-database-secret'  # これをDeploymentのenvに指定する
        },
        'spec': {
            'backendType': 'secretsManager',
            'data': [
                {
                    'key': rds_instance.secret.secret_name,
                    'name': 'password',
                    'property': 'password'
                },
                {
                    'key': rds_instance.secret.secret_name,
                    'name': 'dbname',
                    'property': 'dbname'
                },
                {
                    'key': rds_instance.secret.secret_name,
                    'name': 'host',
                    'property': 'host'
                },
                {
                    'key': rds_instance.secret.secret_name,
                    'name': 'username',
                    'property': 'username'
                }
            ]
        }
    }
    return external_secret_manifest
