# Звіт: лабораторна робота 7 — Observability та відкат за метриками

**Проєкт:** TrackHub · **Середовище:** Docker Desktop, Minikube, Kubernetes, Argo CD, Argo Rollouts · **Дата виконання:** 5 листопада 2026 року.

## 1. Розгортання стека спостереження через GitOps

У `argocd-apps/` додано Argo CD Applications для kube-prometheus-stack (Prometheus, Alertmanager, Grafana), Loki та Grafana Alloy. На момент завершення всі застосунки `Synced/Healthy`, а довготривалі поди моніторингу `Running`. Стан підтверджують [застосунки](evidence/applications.txt) і [поди](evidence/monitoring-pods.txt). Grafana доступна локально через перенаправлення порту, наведене в [інструкції](README.md).

**Скріншот для захисту:** [дашборд Grafana](evidence/grafana-dashboard.png), на якому видно, що Grafana працює і завантажила дашборд із Git.

## 2. Метрики застосунку та ServiceMonitor

TrackHub віддає `/metrics`. Лічильник `trackhub_http_requests_total` має мітки `method`, `route` і `status`; гістограма `trackhub_http_request_duration_seconds` вимірює затримку. Для `route` використовується шаблон маршруту, а не конкретний ідентифікатор об'єкта. Helm chart створює `ServiceMonitor` для Prometheus.

**Скріншоти для захисту:** [шість цілей TrackHub у стані UP](evidence/prometheus-targets.png) і [виконаний PromQL-запит до лічильника](evidence/prometheus-query.png).

## 3. Структуровані логи та Loki

Застосунок пише в stdout JSON з полями `time`, `level`, `message`, `method`, `route`, `status`, `duration_ms`. Alloy надсилає логи подів у Loki. У Grafana Explore запит `{namespace="trackhub",container="trackhub",pod="trackhub-6dd65bc794-b5ff9"} | json | status >= 500` показав помилки canary-пода.

**Скріншот для захисту:** [відфільтровані 5xx логи в Grafana Explore](evidence/grafana-error-logs.png).

## 4. Дашборд із Git

JSON дашборда зберігається в `charts/trackhub/dashboards/trackhub-observability.json` і доставляється через ConfigMap із міткою `grafana_dashboard`. Дашборд має панелі RPS, частки 5xx, p95, CPU, пам'яті та логів Loki.

**Скріншот для захисту:** [TrackHub · Observability and Canary](evidence/grafana-dashboard.png). На ньому видно зміну метрик під час тесту помилкової версії.

## 5. Навантаження та зміна кількості реплік

Генератор запитів знаходиться в `scripts/lab7_observability_load.py`. Кількість реплік змінено через Git з 5 до 6; Argo CD застосував зміну. Знімки Prometheus під навантаженням:

| Стан | Реплік / цілей UP | RPS | p95, мс | CPU, cores | Пам'ять, MB | Частка 5xx |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| До зміни | 5 / 5 | 36,85 | 61,63 | 0,300 | 321 | 0% |
| Після зміни | 6 / 6 | 30,84 | 57,26 | 0,267 | 388 | 0% |

Джерела: [5 реплік](evidence/baseline.json), [6 реплік](evidence/scaled.json). Це короткі вибірки за різних моментів навантаження; вони демонструють реакцію дашборда та стан цілей, але не доводять приріст пропускної здатності від масштабування. Після збільшення реплік у вибірці зменшилися p95 і CPU, а сумарна пам'ять зросла.

**Скріншоти для захисту:** [цілі Prometheus](evidence/prometheus-targets.png), [дашборд під навантаженням](evidence/grafana-dashboard.png). Коміти Git із зміною кількості реплік і конфігурації збережені в історії репозиторію.

## 6. Автоматичне припинення помилкового rollout та відновлення

Helm chart містить `AnalysisTemplate`: Prometheus вимірює частку успішних HTTP-відповідей саме нового canary-пода за міткою `rollouts_pod_template_hash`. Поріг успіху — **не менше 95%**. У canary-стратегії AnalysisRun запускається після початкової паузи.

Під час роботи генератора запитів через Git встановлено `config.failRate: 0.8`. Нова ревізія `6dd65bc794` дала 5xx. Prometheus зафіксував частку успішних відповідей canary **0,2053**, нижче порога 0,95. `AnalysisRun` перейшов у `Failed`, Argo Rollouts автоматично припинив просування нової ревізії, а стабільні шість подів залишилися доступними. Далі `config.failRate` повернуто до `0` окремим Git-комітом; Argo CD синхронізував застосунок, rollout знову `Healthy`, 6/6 подів готові.

Під час тесту генератор виконав **17 862** запити: 17 072 відповідей HTTP 200, 786 відповідей HTTP 500 і 4 транспортні помилки. Середній зріз Prometheus під час помилкової ревізії: 97,42 RPS, глобальна частка 5xx 10,88%, успішність canary 18,91%. Після відновлення частка 5xx у контрольному зрізі дорівнювала 0%. Дані: [лог навантаження](evidence/load-bad.txt), [зріз помилкової версії](evidence/bad-canary.json), [AnalysisRun](evidence/failed-analysisrun.json), [стан після відновлення](evidence/recovered.json).

**Скріншоти для захисту:** [провал AnalysisRun](evidence/failed-analysis-measurement.png), [історія ревізій і стабільні поди](evidence/argo-rollout-history.png), [сплеск 5xx на дашборді](evidence/grafana-dashboard.png), [логи нового пода](evidence/grafana-error-logs.png). Текстові докази: [rollout після abort](evidence/aborted-rollout.txt), [стабільні поди](evidence/stable-pods-after-abort.txt), [здоровий rollout після повернення конфігурації](evidence/healthy-rollout.txt).

## 7. Перевірка під час захисту

Відкрити Grafana, Prometheus та Argo Rollouts за [інструкцією](README.md). Показати дашборд, метрику в Prometheus, 5xx логи в Loki, історичний `AnalysisRun Failed` і поточний `Healthy` стан. Поточні [Argo CD Applications](evidence/applications.txt), [поди TrackHub](evidence/trackhub-pods.txt) і скріншоти вище дозволяють показати завершену роботу без повторного запуску помилкової версії.

**Підсумок:** автоматичним був abort помилкової canary-ревізії. Повернення значення `failRate` у Git виконано окремим комітом, після чого GitOps відновив бажаний здоровий стан.
