import json
import os
import uuid
from datetime import datetime, timezone
import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "trackhub-items")


def get_dynamodb_table():
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint_url:
        host = os.environ.get("LOCALSTACK_HOSTNAME")
        endpoint_url = f"http://{host}:4566" if host else "http://127.0.0.1:4566"
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1", endpoint_url=endpoint_url)
    return dynamodb.Table(TABLE_NAME)


def build_response(status_code: int, body: dict | list):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def lambda_handler(event, context):
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    path_params = event.get("pathParameters") or {}

    item_id = path_params.get("id")
    if not item_id and path.startswith("/items/") and len(path.split("/")) == 3:
        item_id = path.split("/")[2]

    try:
        table = get_dynamodb_table()

        # 1. Створення запису (POST /items)
        if http_method == "POST" and path.rstrip("/") == "/items":
            raw_body = event.get("body") or "{}"
            data = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            if not data.get("title"):
                return build_response(400, {"error": "Field 'title' is required"})

            new_item = {
                "id": str(uuid.uuid4())[:8],
                "title": data["title"],
                "status": data.get("status", "open"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            table.put_item(Item=new_item)
            return build_response(201, {"message": "Item created", "item": new_item})

        # 2. Отримання одного запису (GET /items/{id})
        if http_method == "GET" and item_id:
            res = table.get_item(Key={"id": item_id})
            item = res.get("Item")
            if not item:
                return build_response(404, {"error": f"Item '{item_id}' not found"})
            return build_response(200, item)

        # 3. Отримання всіх записів (GET /items)
        if http_method == "GET" and path.rstrip("/") == "/items":
            res = table.scan()
            items = res.get("Items", [])
            return build_response(200, {"count": len(items), "items": items})

        # 4. Видалення запису (DELETE /items/{id})
        if http_method == "DELETE" and item_id:
            res = table.get_item(Key={"id": item_id})
            if not res.get("Item"):
                return build_response(404, {"error": f"Item '{item_id}' not found"})
            table.delete_item(Key={"id": item_id})
            return build_response(200, {"message": f"Item '{item_id}' deleted"})

        return build_response(404, {"error": f"Route {http_method} {path} not found"})

    except Exception as exc:
        return build_response(500, {"error": str(exc)})
