# ЛР 7: Observability та відкат за метриками

Ця лабораторна стосується TrackHub у Minikube з Argo CD та Argo Rollouts.
Попередня `docs/lab7` є окремою лабораторною про шардинг даних.

## Що розгортається з Git

- `argocd-apps/monitoring.yaml`: kube-prometheus-stack, включно з Prometheus,
  Alertmanager і Grafana. Prometheus шукає ServiceMonitor у всіх namespace.
- `argocd-apps/loki.yaml`: Loki у режимі Monolithic з однією реплікою.
- `argocd-apps/alloy.yaml`: Alloy збирає stdout логів подів TrackHub у Loki.
- `charts/trackhub`: `/metrics`, ServiceMonitor, AnalysisTemplate і дашборд
  `charts/trackhub/dashboards/trackhub-observability.json`.

## Перевірки та місця для скріншотів

1. **Стек моніторингу.** `kubectl get applications -n argocd` і
   `kubectl get pods -n monitoring`. Зберегти екран із `Healthy/Synced`
   для трьох застосунків і подами `Running`. Відкрити Grafana:
   `kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80`,
   далі `http://localhost:3000`. Пароль отримати командою
   `kubectl -n monitoring get secret kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}"`
   і декодувати Base64 локально. Зробити скрін Grafana.
2. **Метрики.** `kubectl -n trackhub get servicemonitor trackhub`.
   У Prometheus `Status → Targets` знайти `trackhub/trackhub` у стані `UP`.
   Виконати `sum(rate(trackhub_http_requests_total{namespace="trackhub"}[1m]))`.
   Зробити два скріни: ціль і результат запиту.
3. **Логи.** У Grafana Explore вибрати Loki і виконати
   `{namespace="trackhub",container="trackhub"} | json`.
   Для помилок: `{namespace="trackhub",container="trackhub"} | json | status >= 500`.
   Зробити скрін результату фільтра.
4. **Дашборд.** Відкрити `TrackHub · Observability and Canary`.
   Показати шість панелей: RPS, 5xx, p95, CPU, пам'ять і логи.
   Зробити скрін дашборда.
5. **Навантаження.** Запустити генератор з окремого пода або з комп'ютера,
   який має доступ до сервісу:

   `python scripts/lab7_observability_load.py --url http://trackhub.trackhub.svc.cluster.local:8000/api/tasks --duration 180 --workers 8`

   На дашборді зафіксувати зміну RPS, p95 і CPU. Додаткова зміна —
   змінити `replicaCount` у `charts/trackhub/values-minikube.yaml` через Git,
   дочекатися синхронізації та зробити ще один скрін.
6. **Автоматичний відкат.** За сталого навантаження змінити
   `config.failRate` з `0` на `0.8` у `values-minikube.yaml`, зробити
   commit і push. Через `kubectl -n trackhub get analysisruns,rollouts` і
   `kubectl argo rollouts get rollout trackhub -n trackhub` показати
   `AnalysisRun Failed` і abort. Зафіксувати сплеск 5xx на дашборді та
   логи помилок у Loki, відфільтровані за назвою нового пода.
   Повернути `config.failRate: 0` через новий commit і push, дочекатися
   `Healthy/Synced`. Для звіту потрібні скріни AnalysisRun, дашборда,
   логів і фінального здорового стану.

## Запити

PromQL для p95:

`histogram_quantile(0.95, sum by (le) (rate(trackhub_http_request_duration_seconds_bucket{namespace="trackhub"}[1m])))`

PromQL для частки успішних запитів нової версії задається у
`charts/trackhub/templates/analysis-template.yaml`. Він використовує
мітку `rollouts_pod_template_hash`, тому стабільні поди не маскують
помилки canary. Успіх вимагає щонайменше 95% HTTP-відповідей без 5xx.

LogQL для помилок конкретного пода:

`{namespace="trackhub",container="trackhub",pod="НАЗВА_ПОДА"} | json | status >= 500`
