# In ide's like vscode, ensure that your are creating v-env using anakonda or minikonda
# conda install boto3

import boto3
import json

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
from custom_encoder import CustomEncoder

dynamodb_table_name = "product-inventory"
resource = "dynamodb" 
region = "us-east-1"

dynamodb_resource = boto3.resource(resource,region_name=region)
table = dynamodb_resource.Table(dynamodb_table_name)


get_method = "GET"
post_method = "POST"
patch_method = "PATCH"
delete_method = "DELETE"
health_path = "/health"
product_path = "/product"
products_path = "/products"
max_product_path = product_path + "/max_product"
min_product_Path = product_path + "/min_product"



def lambda_handler(event, context):
    json_event = json.dumps(event, cls=CustomEncoder)
    logger.info(json_event)
    # print(event.get("httpMethod"))
    # return {
    #     'statusCode': 200,
    #     'body': json.dumps('Hello from Lambda!')
    # }
    http_method = event.get("httpMethod")
    path = event.get("path")

    # health_path = "/health" method = GET
    if http_method == get_method and path == health_path:
        response = build_response(200)

    # product_path = "/product/{product_id}"  method = GET
    elif http_method == get_method and path == product_path:
        response = get_product(event["queryStringParameters"]["product_id"])

    # products_path = "/products"   method = GET
    elif http_method == get_method and path == products_path:
        response = get_products()

    # product_path = "/product"   method = POST
    elif http_method == post_method and path == product_path:
        response = save_product(json.loads(event["body"]))

    # product_path = "/product"   method = PATCH
    elif http_method == patch_method and path == product_path:
        response = modify_product(json.loads(event["body"]))

    # product_path = "/product"   method = DELETE
    elif http_method == delete_method and path == product_path:
        response = delete_product(json.loads(event["body"]))
        
    # min_product_path = "/product/min_product"  method = GET
    elif http_method == get_method and path == min_product_Path:
        response = get_min_product()

    # max_product_path = "/product/max_product"  method = GET
    elif http_method == get_method and path == max_product_path:
        response = get_max_product()

    else:
        response = build_response(404, "Not Found")

    # finally return the response
    return response


def get_product(product_id):
    try:
        response = table.get_item(
            Key={
                "product_id": product_id
            }
        )
        print(response)
        if "Item" in response:
            return build_response(200, response["Item"])
        else:
            return build_response(404, {"Message": "Product id {} not found".format(product_id)})
    except Exception as e:
        logger.exception("Error getting product: %s", e)
        return build_response(500, {"Message": "Something went wrong"})


def get_products():
    try:
        response = table.scan()
        result = response["Items"]
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            result.extend(response["Items"])
        body = {
            "products": result
        }
        return build_response(200, body)
    except Exception as e:
        logger.exception("Error getting products: %s", e)
        return build_response(500, {"Message": "Something went wrong"})
  

def save_product(request_body):
    try:
        table.put_item(Item=request_body)
        body = {
            "Operation": "SAVE",
            "Message": "SUCCESS",
            "Item": request_body
        }
        return build_response(200, body)
    except Exception as e:
        logger.exception("Error saving product: %s", e)
        return build_response(500, {"Message": "Something went wrong"})
    

def modify_product(request_body):
    try:
        update_expression = "set "
        expression_attribute_values = {}
        
        # Ensure product_id is present
        if "product_id" not in request_body:
            return build_response(400, {"Message": "Missing product_id in the request body"})
        
        product_id = request_body.pop("product_id")  # Remove product_id from request_body to avoid trying to update it
        
        # Construct update expression and attribute values
        for key, value in request_body.items():
            update_expression += f"{key} = :{key}, "
            expression_attribute_values[f":{key}"] = value
        
        # Remove trailing comma and space from the update expression
        update_expression = update_expression.rstrip(", ")
        
        response = table.update_item(
            Key={"product_id": product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW",
        )
        
        body = {
            "Operation": "UPDATE",
            "Message": "SUCCESS",
            "UpdatedAttributes": response.get("Attributes", {})
        }
        return build_response(200, body)
        
    except Exception as e:
        logger.exception("Error updating product: %s", e)
        return build_response(500, {"Message": "Something went wrong"})



def delete_product(request_body):
    try:
        product_id = request_body["product_id"]
        response = table.delete_item(
            Key={
                "product_id": product_id
            },
            ReturnValues="ALL_OLD"
        )
        deleted_item = response.get("Attributes", {})
        body = {
            "Operation": "DELETE",
            "Message": "SUCCESS",
            "Item": deleted_item
        }
        return build_response(200, body)
    except Exception as e: 
        logger.exception("Error deleting product: %s", e)
        return build_response(500, {"Message": "Something went wrong"})
    

def get_min_product():
    try:
        response = table.scan()
        result = response["Items"]
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            result.extend(response["Items"])
        min_products = []
        min_product = min(result, key=lambda x: x["price"])
        for product in result:
            if product["price"] == min_product["price"]:
                min_products.append(product)
        body = {
            "min_products": min_products 
        }
        return build_response(200, body)
    except Exception as e:
        logger.exception("Error getting min product: %s", e)
        return build_response(500, {"Message": "Something went wrong"})
    
def get_max_product():
    try:
        response = table.scan()
        result = response["Items"]
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            result.extend(response["Items"])
        max_products = []
        max_product = max(result, key=lambda x: x["price"])
        for product in result:
            if product["price"] == max_product["price"]:
                max_products.append(product)
        body = {
            "max_products": max_products
        }
        return build_response(200, body)
    except Exception as e:
        logger.exception("Error getting max product: %s", e)
        return build_response(500, {"Message": "Something went wrong"})

def build_response(status_code,body=None):
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        }
    }
    if body is not None:
        response["body"] = json.dumps(body, cls=CustomEncoder)
        # python => json = (dumps) => js (response.body)
        # json => python = (loads) => js (JSON.parse)
    return response