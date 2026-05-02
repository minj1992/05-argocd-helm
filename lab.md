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

## 🔹 2. Application Workflow & Enterprise Architecture
This diagram illustrates how the frontend connects to specialized microservices, utilizing **RabbitMQ** for event-driven auditing and **Redis** for real-time dashboard updates.

```text
+----------+      +------------------+      +-----------------------+
|   User   | ---> | Frontend WebApp  | ---> | Auth Microservices    |
+----------+      | (NodePort 30007) |      | (Login, Register, etc)|
                  +---------+--------+      +-----------+-----------+
                            |                           |
                            |           +---------------+---------------+
                            |           |                               |
                            v           v                               v
                  +-----------------------+                 +-----------------------+
                  |    RabbitMQ (MQ)      |                 |    MySQL Database     |
                  | (Event-Driven Bus)    |                 | (Relational Storage)  |
                  +-----------+-----------+                 +-----------------------+
                            |
                            v
                  +-----------------------+                 +-----------------------+
                  |    Audit Service      | -------->       |     Redis Cache       |
                  | (Event Consumer)      |                 | (Live Dash Metrics)   |
                  +-----------+-----------+                 +-----------+-----------+
                            |                                           |
                            +-------------------------------------------+
                                            |
                                            v
                                  +-----------------------+
                                  | Enterprise Dashboard  |
                                  | (Live Logs & Metrics) |
                                  +-----------------------+
```

## 🔹 3. ArgoCD App-of-Apps Workflow
The root application manages the lifecycle of individual microservice applications, ensuring a clean separation between infrastructure management and application logic.

```text
+-----------------------+          +-----------------------+
|    Git Repository     | -------> |    ArgoCD Server      |
| (Desired State YAML)  |          | (Controller/UI)       |
+-----------------------+          +-----------+-----------+
                                               |
                                               v
                                   +-----------------------+
                                   |   Root Application    |
                                   |  (root-argocd.yaml)   |
                                   +-----------+-----------+
                                               |
         +-------------------------------------+-------------------------------------+
         |                                     |                                     |
         v                                     v                                     v
+-----------------------+           +-----------------------+           +-----------------------+
|   Child-Frontend      |           |   Child-Auth Apps     |           |   Child-Infra Apps    |
| (App-specific YAML)   |           | (App-specific YAML)   |           | (App-specific YAML)   |
+-----------+-----------+           +-----------+-----------+           +-----------+-----------+
            |                                   |                                   |
            v                                   v                                   v
+-----------------------+           +-----------------------+           +-----------------------+
| Kubernetes Resources  |           | Kubernetes Resources  |           | Kubernetes Resources  |
| (Deploy, SVC, PVC)    |           | (Deploy, SVC, Secret) |           | (MySQL, Redis, MQ)    |
+-----------------------+           +-----------------------+           +-----------------------+
```

## 🔹 4. Real-time Event-Driven Architecture (RabbitMQ Flow)
Each microservice communicates asynchronously via RabbitMQ for real-time auditing and side effects. The **Audit Service** acts as a bridge between the event bus and the **Enterprise Dashboard**.

```text
[ Microservices ] ---▶ [ RabbitMQ Exchange ] ---▶ [ Audit Worker ]
                                                        │
                                                        ▼
[ Dashboard UI ]  ◀--- [ Redis Event Cache ] ◀---------┘
```

### 🔹 Enterprise Monitoring Features:
- **Live Audit Log**: Tracks "Transaction Paths" (e.g., `LOGIN ──▶ AUDIT_LOG`) in real-time.
- **Cache Health**: Displays live Redis memory usage and hit rates.
- **Database Metrics**: Automatic discovery of active tables and user counts.
- **Architecture-as-Code**: The Frontend renders `lab.md` directly into the UI for documentation accessibility.

## 🔹 5. Build and Push (Detailed Steps)

### Step 1: Login to Docker
```bash
docker login -u minjteck
```

### Step 2: Build Microservices

**1. Audit Service**
```bash
cd apps/audit/app
docker build -t minjteck/audit-service:v1 .
docker push minjteck/audit-service:v1
cd ../../..
```

**2. Frontend Service**
```bash
cd apps/frontend/app
docker build -t minjteck/frontend-service:v1 .
docker push minjteck/frontend-service:v1
cd ../../..
```

**3. Login Service**
```bash
cd apps/login/app
docker build -t minjteck/login-service:v1 .
docker push minjteck/login-service:v1
cd ../../..
```

**4. Register Service**
```bash
cd apps/register/app
docker build -t minjteck/register-service:v1 .
docker push minjteck/register-service:v1
cd ../../..
```

**5. Profile Service**
```bash
cd apps/profile/app
docker build -t minjteck/profile-service:v1 .
docker push minjteck/profile-service:v1
cd ../../..
```

**6. Forgot Password Service**
```bash
cd apps/forgot-password/app
docker build -t minjteck/forgot-password-service:v1 .
docker push minjteck/forgot-password-service:v1
cd ../../..
```

**7. Logout Service**
```bash
cd apps/logout/app
docker build -t minjteck/logout-service:v1 .
docker push minjteck/logout-service:v1
cd ../../..
```

## 🔹 6. Deployment Steps
1. **Initialize Root App**: `kubectl apply -f root-argocd.yaml`
2. **ArgoCD Cascading**: The root app creates the child apps, which then create the manifests for each service.

## 🔹 7. Validation
### Default Admin Credentials
Use the following credentials to log into the web application:
- **Username**: `admin`
- **Email**: `admin@devops.com`
- **Password**: `admin`

### Check Real-time Events
To see the RabbitMQ communication in action:
```bash
kubectl logs -f deployment/audit-service -n enterprise-lab
```
Now, go to the Frontend UI, login or register, and you will see the **[AUDIT]** logs appear instantly in your terminal!
