import boto3
from moto import mock_dynamodb

from tap_dynamodb.dynamo import DynamoDB


def create_table(moto_conn, name):
    return moto_conn.create_table(
        TableName=name,
        KeySchema=[
            {"AttributeName": "year", "KeyType": "HASH"},
            {"AttributeName": "title", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "year", "AttributeType": "N"},
            {"AttributeName": "title", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )


@mock_dynamodb
def test_list_tables():
    # PREP
    moto_conn = boto3.resource("dynamodb", region_name="us-west-2")
    for num in range(1, 106):
        create_table(moto_conn, f"table_{num}")
    # END PREP

    db_obj = DynamoDB()
    db_obj._client = moto_conn
    tables = db_obj.list_tables()
    assert len(tables) == 105
    assert tables[0] == "table_1"
    assert tables[-1] == "table_105"


@mock_dynamodb
def test_get_items():
    # PREP
    moto_conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = create_table(moto_conn, "table")
    table.put_item(Item={"year": 2023, "title": "foo", "info": {"plot": "bar"}})
    # END PREP

    db_obj = DynamoDB()
    db_obj._client = moto_conn
    records = list(db_obj.get_items_iter("table"))[0]
    assert len(records) == 1
    # Type coercion
    assert records[0].get("year") == "2023"
    assert records[0].get("title") == "foo"
    assert records[0].get("info") == {"plot": "bar"}


@mock_dynamodb
def test_get_items_paginate():
    # PREP
    moto_conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = create_table(moto_conn, "table")
    for num in range(5):
        table.put_item(
            Item={"year": 2023, "title": f"foo_{num}", "info": {"plot": "bar"}}
        )
    # END PREP

    db_obj = DynamoDB()
    db_obj._client = moto_conn
    iterations = 0
    records = []
    for i in db_obj.get_items_iter("table", {"Limit": 1, "ConsistentRead": True}):
        iterations += 1
        records.extend(i)
    assert len(records) == 5
    assert iterations == 5
    first_item = records[0]
    assert first_item.get("year") == "2023"
    assert first_item.get("title") == "foo_0"
    assert first_item.get("info") == {"plot": "bar"}


@mock_dynamodb
def test_get_table_json_schema():
    # PREP
    moto_conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = create_table(moto_conn, "table")
    for num in range(5):
        table.put_item(
            Item={"year": 2023, "title": f"foo_{num}", "info": {"plot": "bar"}}
        )
    # END PREP

    db_obj = DynamoDB()
    db_obj._client = moto_conn
    schema = db_obj.get_table_json_schema("table")
    assert schema == {
        "type": "object",
        "properties": {
            "year": {"type": "string"},
            "title": {"type": "string"},
            "info": {"type": "object", "properties": {"plot": {"type": "string"}}},
        },
    }


def test_coerce_types():
    import decimal
    db_obj = DynamoDB()
    coerced = db_obj._coerce_types(
        {
            "foo": decimal.Decimal("1.23")
        }
    )
    assert coerced == {
        "foo": "1.23"
    }
