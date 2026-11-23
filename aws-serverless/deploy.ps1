$ErrorActionPreference = "Stop"

$ENDPOINT = "http://127.0.0.1:4566"
$TABLE_NAME = "trackhub-items"
$FUNCTION_NAME = "trackhub-handler"
$API_NAME = "trackhub-api"
$STAGE_NAME = "dev"

Write-Host "=== 1. Checking LocalStack health ===" -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "$ENDPOINT/_localstack/health"
Write-Host "DynamoDB: $($health.services.dynamodb) | Lambda: $($health.services.lambda) | API Gateway: $($health.services.apigateway)"

Write-Host "`n=== 2. Creating DynamoDB table ($TABLE_NAME) ===" -ForegroundColor Cyan
$tables = aws --endpoint-url=$ENDPOINT dynamodb list-tables --query "TableNames" --output text
if ($tables -notmatch $TABLE_NAME) {
    aws --endpoint-url=$ENDPOINT dynamodb create-table `
        --table-name $TABLE_NAME `
        --attribute-definitions AttributeName=id,AttributeType=S `
        --key-schema AttributeName=id,KeyType=HASH `
        --billing-mode PAY_PER_REQUEST | Out-Null
    Write-Host "Table $TABLE_NAME created."
} else {
    Write-Host "Table $TABLE_NAME already exists."
}

Write-Host "`n=== 3. Packaging and deploying AWS Lambda ($FUNCTION_NAME) ===" -ForegroundColor Cyan
Compress-Archive -Path .\lambda_function.py -DestinationPath .\function.zip -Force

$existingFunc = aws --endpoint-url=$ENDPOINT lambda list-functions --query "Functions[?FunctionName=='$FUNCTION_NAME'].FunctionName" --output text
if ($existingFunc -eq $FUNCTION_NAME) {
    aws --endpoint-url=$ENDPOINT lambda delete-function --function-name $FUNCTION_NAME | Out-Null
}

aws --endpoint-url=$ENDPOINT lambda create-function `
    --function-name $FUNCTION_NAME `
    --runtime python3.11 `
    --handler lambda_function.lambda_handler `
    --role arn:aws:iam::000000000000:role/lambda-role `
    --zip-file fileb://function.zip `
    --environment "Variables={TABLE_NAME=$TABLE_NAME}" | Out-Null

aws --endpoint-url=$ENDPOINT lambda wait function-active-v2 --function-name $FUNCTION_NAME
Write-Host "Lambda function $FUNCTION_NAME is Active."

Write-Host "`n=== 4. Configuring API Gateway ($API_NAME) ===" -ForegroundColor Cyan
$oldApis = aws --endpoint-url=$ENDPOINT apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text
foreach ($id in ($oldApis -split "\s+")) {
    if ($id) {
        aws --endpoint-url=$ENDPOINT apigateway delete-rest-api --rest-api-id $id | Out-Null
    }
}

$API_ID = aws --endpoint-url=$ENDPOINT apigateway create-rest-api --name $API_NAME --query "id" --output text
$ROOT_ID = aws --endpoint-url=$ENDPOINT apigateway get-resources --rest-api-id $API_ID --query "items[0].id" --output text
$PROXY_ID = aws --endpoint-url=$ENDPOINT apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_ID --path-part "{proxy+}" --query "id" --output text

aws --endpoint-url=$ENDPOINT apigateway put-method --rest-api-id $API_ID --resource-id $PROXY_ID --http-method ANY --authorization-type NONE | Out-Null
aws --endpoint-url=$ENDPOINT apigateway put-integration `
    --rest-api-id $API_ID `
    --resource-id $PROXY_ID `
    --http-method ANY `
    --type AWS_PROXY `
    --integration-http-method POST `
    --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:000000000000:function:${FUNCTION_NAME}/invocations" | Out-Null

aws --endpoint-url=$ENDPOINT apigateway create-deployment --rest-api-id $API_ID --stage-name $STAGE_NAME | Out-Null

$BASE_URL = "$ENDPOINT/restapis/$API_ID/$STAGE_NAME/_user_request_"
Write-Host "`nDeploy completed successfully!" -ForegroundColor Green
Write-Host "Base URL: $BASE_URL" -ForegroundColor Yellow