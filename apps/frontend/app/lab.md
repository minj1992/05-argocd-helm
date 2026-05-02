# Lab 04: Nishant DevOps Class - Enterprise Microservices

## 🔹 1. Git Repository Structure
This lab follows a strict **App-of-Apps** pattern with deep separation of concerns.

```text
04-argocd/
├── root-argocd.yaml          # Root Application
│
├── argocd/                   # ArgoCD Child Manifests (Child Prefix)
│   ├── child-frontend-microservice.yaml
│   ├── child-login-microservice.yaml
│   ├── child-audit-microservice.yaml
│   └── ... 
│
├── argocd/manifests/         # Kubernetes Resources (Dedicated Files)
│   ├── login/
│   │   ├── deployment.yaml   # Includes PVC & Secret integration
│   │   ├── service.yaml
│   │   ├── pvc.yaml
│   │   ├── storageclass.yaml
│   │   ├── secret.yaml
│   │   └── configmap.yaml
│   └── ...
│
└── apps/                     # Application Source Code
    ├── login/app/
    │   ├── app.py
    │   ├── mq_helper.py      # Shared Event Publisher
    │   └── Dockerfile
    └── ...
```

## 🔹 2. Real-time Event-Driven Architecture (RabbitMQ Flow)
Each microservice communicates asynchronously via RabbitMQ for real-time auditing and side effects.

```text
[ Frontend ]
     │
     ▼ (REST)
+------------------+       (Event Publish)       +-------------------+
|  Auth Services   | --------------------------▶ |   RabbitMQ Broker |
| (Login/Register) |       topic: user.#         |   (Exchange)      |
+------------------+                             +---------┬---------+
                                                           │
                                                           ▼ (Async)
                                                 +-------------------+
                                                 |   Audit Service   |
                                                 | (Real-time Logger)|
                                                 +-------------------+
```

### 🔹 Logic Flow:
1. **Action**: User registers or logs in via Frontend.
2. **Backend**: Service (e.g., `login`) performs logic and calls `publish_event()`.
3. **Broker**: RabbitMQ receives the message on the `enterprise_events` exchange.
4. **Consumer**: The **Audit Service** (Worker) consumes the message from its queue in real-time.
5. **Visibility**: You can see these events by checking the `audit-service` logs.

## 🔹 3. Build and Push (Detailed Steps)

### Step 1: Login to Docker
```bash
docker login -u minjteck
```

### Step 2: Build Microservices
```bash
# Example for Audit Service
cd apps/audit/app
docker build -t minjteck/audit-service:v1 .
docker push minjteck/audit-service:v1

# Repeat for: frontend, login, register, profile, forgot-password, logout
```

## 🔹 4. Deployment Steps
1. **Initialize Root App**: `kubectl apply -f root-argocd.yaml`
2. **ArgoCD Cascading**: The root app creates the child apps, which then create the manifests for each service.

## 🔹 5. Validation
### Check Real-time Events
To see the RabbitMQ communication in action:
```bash
kubectl logs -f deployment/audit-service -n enterprise-lab
```
Now, go to the Frontend UI, login or register, and you will see the **[AUDIT]** logs appear instantly in your terminal!
