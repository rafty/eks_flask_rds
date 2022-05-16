import json
import pprint
from os import environ
import pymysql
import boto3


secrets_manager = boto3.client('secretsmanager')
secret_value = secrets_manager.get_secret_value(
    SecretId=environ['DB_SECRET_MANAGER_ARN']
)
database_secrets = json.loads(secret_value['SecretString'])

print('Secrets Manager')
pprint.pprint(database_secrets)

try:
    connect = pymysql.connect(
        host=database_secrets['host'],
        user=database_secrets['username'],
        passwd=database_secrets['password'],
        db=database_secrets['dbname']
    )

except pymysql.MySQLError as e:
    print(f'Error: {e}')
    raise

queries = [
    """
CREATE TABLE IF NOT EXISTS listings (
    id INT PRIMARY KEY, 
    name VARCHAR(90), 
    neighbourhood VARCHAR(65),
    latitude DOUBLE,
    longitude DOUBLE,
    room_type VARCHAR(25),
    price INT
)"""
]


def handler(event, context):

    item_count = 0

    with connect.cursor() as cur:
        for query in queries:
            cur.execute(query)
            item_count += 1

        connect.commit()

    connect.commit()

    return {'status': 'ok', 'item_count': item_count}
