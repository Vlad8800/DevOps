## Helm-чарт TrackHub (Lab #4)

Для ЛР-5 чарт розміщено в `charts/trackhub`. Файл
`charts/trackhub/values-minikube.yaml` містить параметри локального кластера.
`bootstrap/trackhub-root.yaml` є єдиним Application, який застосовується
вручну після встановлення Argo CD. Він створює дочірній Application із
`argocd-apps/trackhub.yaml`; дочірній Application читає чарт і values з Git.

Не зберігайте справжні паролі й токени у файлах values. Якщо вони потрібні,
створіть Kubernetes Secret поза Git та передайте його назву через
`secrets.existingSecret`. Для локальної конфігурації використовується SQLite
без пароля, тому Secret не потрібен.
Старий `k8s/secret.yaml` з ЛР-3 вилучено з поточної версії репозиторію;
локальний файл із цією назвою ігнорується Git.

Початковий `selfHeal: false` у дочірньому Application потрібен для демонстрації
дрейфу. Після цього досліду його треба змінити на `true` у Git.

### Різниця між `version` та `appVersion`
- **`version`** (`0.1.0`): семантична версія самого Helm-чарта (його шаблонів, конфігурації `values.yaml` та структури).
- **`appVersion`** (`1.0.0`): версія пакованого застосунку (Docker-образу TrackHub), яка не залежить від версії інфраструктурних маніфестів.

### Параметри чарта (`values.yaml`)

| Параметр | Опис | За замовчуванням |
| :--- | :--- | :--- |
| `replicaCount` | Кількість реплік подів | `1` |
| `image.repository` | Реєстр та назва образу | `ghcr.io/vlad8800/devops` |
| `image.tag` | Тег образу | `1.0.0` |
| `service.type` | Тип сервісу K8s | `ClusterIP` |
| `service.port` | Порт сервісу | `8000` |
| `ingress.enabled` | Увімкнення Ingress | `false` |
| `config.appEnv` | Змінна середовища застосунку | `development` |
| `config.databaseUrl`| Локальний рядок підключення до SQLite | `sqlite:///./dev.db` |
| `secrets.existingSecret`| Назва вже створеного Secret, якщо потрібен | порожньо |

### Пріоритет значень у Helm
Значення під час рендерингу мають такий пріоритет (від найнижчого до найвищого):
1. Значення за замовчуванням у `values.yaml`.
2. Значення з файлу середовища (`-f values-dev.yaml` або `-f values-prod.yaml`).
3. Явні перевизначення прапорцем у командному рядку (`--set key=value`).
