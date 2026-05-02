# Lab 05: Enterprise GitOps with Helm & ArgoCD

## 🔹 1. Git Repository Structure
This lab transitions from static YAML manifests to a **Centralized Helm Chart** pattern. Each microservice now uses a common base chart, providing its own `values.yaml`.

```text
05-argocd-helm/
├── root-argocd.yaml          # Root Application (Helm-enabled)
│
├── charts/                   # Centralized Enterprise Chart
│   └── enterprise-service/   # Base templates for all services
│       ├── Chart.yaml
│       ├── values.yaml       # Default global values
│       └── templates/        # Reusable Deployment, SVC, Secret templates
│
├── argocd/                   # ArgoCD Child Manifests
│   ├── child-frontend-microservice.yaml
│   └── ... 
│
├── argocd/manifests/         # Service-specific Helm Charts
│   ├── frontend/
│   │   ├── Chart.yaml        # References ../../../charts/enterprise-service
│   │   └── values.yaml       # Frontend-specific overrides
│   └── ...
│
└── apps/                     # Application Source Code
    └── ...
```

## 🔹 2. Centralized Helm Architecture
By using a centralized chart, we reduce boilerplate code. Instead of managing 10 separate Deployment YAMLs, we manage one template and 10 small `values.yaml` files.

```text
+-----------------------+          +-----------------------+
|  Centralized Chart    | <------- |   Microservice App    |
| (enterprise-service)  |          | (login, audit, etc.)  |
+-----------+-----------+          +-----------+-----------+
            |                                  |
            v                                  v
    [ Shared Templates ]               [ Service Values ]
    (Deploy, SVC, PVC)                 (Image, Env, Port)
```

## 🔹 3. Helm dependency Management
Each microservice chart in `argocd/manifests/` defines the centralized chart as a local dependency. ArgoCD automatically runs `helm dependency build` before applying the resources.

**Example `Chart.yaml` for a service:**
```yaml
dependencies:
  - name: enterprise-service
    version: 0.1.0
    repository: "file://../../../charts/enterprise-service"
```

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

## 🔹 4. Automated Build and Deploy
The provided automation script `rebuild_and_deploy.sh` has been updated to support the new Helm structure. It builds images, pushes them, and updates the `tag` in `values.yaml` for each service.

### Usage:
```bash
# Run the script with a new tag (e.g., v10)
./rebuild_and_deploy.sh v10
```

---

## 🔹 5. Manual Build and Push (Detailed Steps)

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

## 🔹 6. Deployment Steps (ArgoCD)
Deploying the enterprise stack with ArgoCD is a two-step process: initializing the root controller and letting it cascade the child microservices.

### Step 1: Create ArgoCD Namespace
If you haven't already installed ArgoCD, create the namespace:
```bash
kubectl create namespace argocd
```

### Step 2: Install ArgoCD (Stable)
```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### Step 3: Deploy Root Application
The Root application manages all microservices. Applying this file will trigger ArgoCD to create 10 child applications:
```bash
kubectl apply -f root-argocd.yaml
```

### Step 4: Access ArgoCD UI
To monitor the sync status visually:
```bash
# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo

# Port forward to localhost:8080
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Step 5: Verify Cascading Sync
ArgoCD will automatically:
1.  Read the `argocd/` folder.
2.  Create Application objects for `login`, `frontend`, `audit`, etc.
3.  Execute `helm dependency build` for each microservice.
4.  Deploy the resources into the `enterprise-lab` namespace.

## 🔹 7. Manifest Architecture & Usage
Each microservice is bundled with specific Kubernetes objects that enable enterprise features:

| Manifest | Purpose | Application Usage |
|----------|---------|-------------------|
| **Deployment** | Pod Management | Defines the Python container, environment variables (`MYSQL_HOST`), and **Liveness Probes** (`/health`). |
| **Service** | Load Balancing | Provides internal DNS names like `login-service-svc` which the Frontend uses for API calls. |
| **Secret** | Security | Holds sensitive DB passwords and Flask `SECRET_KEY`, injected as environment variables. |
| **ConfigMap** | Configuration | Stores non-sensitive data like DB names or RabbitMQ URLs. |
| **PVC / SC** | Persistence | Ensures MySQL and Redis data survives pod restarts. Used for the `/data` mount point. |
| **RBAC** | Permissions | (Frontend Only) Allows the Python code to query `kubectl` style data from within the pod. |

## 🔹 8. Validation
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

---

## 🔹 9. Cleanup
To remove all resources created by this lab, use the following commands:

### 1. Delete Root Application
```bash
# Delete the root application
kubectl delete -f root-argocd.yaml
```

### 2. Delete All Child Applications
If child applications are still running in the ArgoCD UI, delete them manually:
```bash
# Delete all applications in the argocd namespace
kubectl delete apps --all -n argocd
```

### 3. Force Delete (If apps are stuck)
If applications are stuck in "Deleting" status, remove their finalizers to force delete:
```bash
# Remove finalizers and delete all apps
kubectl get apps -n argocd -o name | xargs -I {} kubectl patch {} -n argocd --type=merge -p '{"metadata":{"finalizers":null}}' && kubectl delete apps --all -n argocd
```

### 4. Remove Namespace
```bash
# (Optional) Delete the application namespace
kubectl delete namespace enterprise-lab
```
