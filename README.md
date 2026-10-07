## Розгортання в Kubernetes (Lab #3 / DVO-L3-7F2A91)

### Параметри конфігурації
- **ConfigMap (`trackhub-config`)**:
  - \`APP_ENV\`: режим роботи застосунку (\`production\`).
  - \`DEFAULT_PRIORITY\`: пріоритет завдань за замовчуванням (\`medium\`).
- **Secret (`trackhub-secret`)**:
  - \`DATABASE_URL\`: рядок підключення до бази даних SQLite (\`sqlite:///./test.db\`).
  - \`API_SECRET_KEY\`: секретний ключ для підпису/автентифікації.

### Порядок розгортання
1. Створення простору імен:
   \`\`\`bash
   kubectl apply -f k8s/namespace.yaml
   \`\`\`
2. Застосування конфігурацій, секретів, розгортання та сервісу:
   \`\`\`bash
   kubectl apply -f k8s/
   \`\`\`
3. Перевірка статусу ресурсів:
   \`\`\`bash
   kubectl get all -n trackhub
   \`\`\`
"@ | Add-Content -Path "README.md" -Encoding utf8
