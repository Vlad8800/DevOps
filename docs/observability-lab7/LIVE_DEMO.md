# Лабораторна 7: живий показ помилкової canary-версії

Це повторення обов'язкового пункту **c**. Пункт **d\*** з PrometheusRule є додатковим і для цього показу не потрібен. Виконуйте команди в PowerShell із кореня репозиторію. **Не запускайте крок 3, поки не готові виконати крок 6.**

## 1. Перевірити здоровий стан

```powershell
cd 'C:\Users\Vlad\Documents\Навчання\DevOps'
docker info --format '{{.ServerVersion}}'
minikube status
kubectl get applications -n argocd
kubectl argo rollouts get rollout trackhub -n trackhub
git status --short
```

Дочекайтеся `Synced/Healthy` та 6/6 готових pod. Поточне `config.failRate` має бути `0`:

```powershell
Select-String -Path '.\charts\trackhub\values-minikube.yaml' -Pattern 'failRate:'
```

Не додавайте до коміту інші локальні зміни; нижче `git add` називає лише потрібний YAML.

## 2. Запустити трафік усередині Kubernetes

```powershell
$demoJob = (kubectl create -f '.\scripts\lab7_live_load_job.yaml' -o jsonpath='{.metadata.name}').Trim()
$demoJob
kubectl logs -n trackhub -f "job/$demoJob"
```

Цей 15-хвилинний Job надсилає запити до Kubernetes Service. Він може потрапляти і на stable, і на canary. Вікно з логами залиште відкритим. **Скрін:** кількість запитів і коди `200` до змін.

## 3. Випустити помилкову версію через Git

У новому PowerShell із кореня репозиторію:

```powershell
& '.\scripts\lab7_set_fail_rate.ps1' -Rate 0.8
git diff -- charts/trackhub/values-minikube.yaml
git add -- charts/trackhub/values-minikube.yaml
git commit -m "lab7 demo: inject canary HTTP failures"
git push origin HEAD:main
```

Argo CD стежить за `main` і автоматично застосує зміну. `failRate: 0.8` породжує HTTP 500 у нових pod для `/api/*`; stable-ревізія лишається без цієї помилки. Якщо push відхилено, **не використовуйте `--force`**: перевірте Git і синхронізуйте гілку перед продовженням.

## 4. Показати failed analysis та abort

Повторюйте ці команди, поки не з'явиться нова ревізія, а потім `Failed`:

```powershell
kubectl get pods -n trackhub
kubectl get analysisruns,rollouts -n trackhub
kubectl argo rollouts get rollout trackhub -n trackhub
```

Canary має кроки 20% трафіку, паузу 60 секунд і Prometheus AnalysisRun. Успіх вимагає щонайменше 95% відповідей без 5xx **саме від pod нової ревізії**. Якщо успішність нижча, AnalysisRun стає `Failed`, а **Argo Rollouts без ручної команди** виконує `RolloutAborted`: вага canary повертається до 0%, її pod зменшуються до нуля, трафік обслуговують шість stable pod. **Не виконуйте крок 6 до появи цього стану та збереження скріншота.** Перевірте також поле abort:

```powershell
kubectl get rollout trackhub -n trackhub -o jsonpath='{.status.abort}'
```

Очікуване значення — `true`. Збережіть ім'я нового pod або hash ревізії з `kubectl get pods` для фільтра в Loki. **Скрін:** `AnalysisRun Failed`, `RolloutAborted`/`Degraded`, `SetWeight: 0`, stable pod 6/6. У вікні навантаження мають з'явитися відповіді `500`, а після abort нові відповіді знову мають бути `200`.

## 5. Показати Grafana й логи лише нової версії

Якщо доступ до Grafana ще не відкрито, у новому PowerShell:

```powershell
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80
```

У браузері відкрийте `http://localhost:3000/d/trackhub-observability`, установіть проміжок **Last 15 minutes** і натисніть **Refresh**. **Скрін:** підвищення `HTTP 5xx share` та інші панелі.

У **Explore → Loki → Code** вставте запит, підставивши фактичне ім'я pod нової ревізії:

```logql
{namespace="trackhub",container="trackhub",pod="ІМ'Я_CANARY_POD"} | json | status >= 500
```

Виберіть часовий проміжок, що охоплює експеримент. **Скрін:** запит, ім'я pod і JSON-записи зі `status: 500`. Loki зберігає ці записи після зменшення canary pod до нуля.

## 6. Завершити відкат через Git

У PowerShell із репозиторієм:

```powershell
& '.\scripts\lab7_set_fail_rate.ps1' -Rate 0
git diff -- charts/trackhub/values-minikube.yaml
git add -- charts/trackhub/values-minikube.yaml
git commit -m "lab7 demo: restore healthy canary configuration"
git push origin HEAD:main
```

Дочекайтеся синхронізації та перевірте:

```powershell
kubectl get applications -n argocd
kubectl argo rollouts get rollout trackhub -n trackhub
```

**Скрін:** Argo CD `Synced/Healthy`, Rollout `Healthy`, 6/6 готових pod і відсутність нових 5xx на Grafana після відновлення.

Автоматичним є **abort невдалої canary-ревізії**. Зміна `failRate` назад на `0` — окремий Git-коміт, який повертає бажаний стан конфігурації. Контрольний експеримент уже виконували 5 листопада; його результати та скріншоти є у [звіті](REPORT.md).
