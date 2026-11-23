# Serverless CRUD API (LocalStack + AWS Lambda + DynamoDB + API Gateway)

Локальний serverless-застосунок для керування задачами (**TrackHub Items**), розгорнутий у середовищі **LocalStack** з використанням **AWS CLI** та **PowerShell**.

## Архітектура

    HTTP Client --> Amazon API Gateway ({proxy+}) --> AWS Lambda (Python 3.11) --> Amazon DynamoDB (trackhub-items)

- **Amazon API Gateway (`trackhub-api`)**: приймає REST-запити через проксі-ресурс `/{proxy+}` (метод `ANY`, інтеграція `AWS_PROXY`).
- **AWS Lambda (`trackhub-handler`)**: обробляє маршрутизатор CRUD-операцій на Python 3.11 із використанням бібліотеки `boto3`.
- **Amazon DynamoDB (`trackhub-items`)**: NoSQL-таблиця з первинним ключем `id` (String) у режимі `PAY_PER_REQUEST`.

## Структура каталогу

- `lambda_function.py` — код обробника подій AWS Lambda.
- `deploy.ps1` — PowerShell-скрипт для автоматичного пакування та розгортання всіх AWS-ресурсів.
- `README.md` — опис архітектури та інструкція із запуску.

## Швидкий старт

1. Запустити LocalStack:

       docker run -d --name localstack -p 4566:4566 -v /var/run/docker.sock:/var/run/docker.sock localstack/localstack:3.8.1

2. Розгорнути інфраструктуру:

       powershell -ExecutionPolicy Bypass -File .\deploy.ps1

## Ендпоінти API

| Метод | Шлях | Опис |
| :--- | :--- | :--- |
| `POST` | `/items` | Створити новий запис (`{"title": "...", "status": "..."}`) |
| `GET` | `/items` | Отримати список усіх записів |
| `GET` | `/items/{id}` | Отримати конкретний запис за ідентифікатором |
| `DELETE` | `/items/{id}` | Видалити запис за ідентифікатором |