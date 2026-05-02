# Repository Guidelines

This repository is an **Enterprise Microservices Lab** that demonstrates the **App-of-Apps** pattern using **ArgoCD**. It features a polyglot microservices architecture with Python/Flask backends, RabbitMQ for event processing, and MySQL/Redis for storage.

## Project Structure & Module Organization

The project follows a strict **App-of-Apps** pattern with a deep separation of concerns:

- **[./apps/](./apps/)**: Contains independent microservices (e.g., `login`, `profile`, `audit`). Each service includes its Flask application, `mq_helper.py` for event publishing, and a `Dockerfile`.
- **[./argocd/](./argocd/)**: Defines the ArgoCD child manifests (using the `child-` prefix).
- **[./argocd/manifests/](./argocd/manifests/)**: Dedicated Kubernetes resources (Deployments, Services, PVCs, Secrets, ConfigMaps) organized by service.
- **[./root-argocd.yaml](./root-argocd.yaml)**: The root application that manages the lifecycle of all child applications.

## Build, Test, and Development Commands

### Build and Push Images
Build each microservice from its respective `apps/<service>/app` directory:
```cmd
docker build -t minjteck/<service-name>:v1 .
docker push minjteck/<service-name>:v1
```

### Deployment
1. **Initialize Root App**: `kubectl apply -f root-argocd.yaml`
2. **ArgoCD Cascading**: The root app triggers the creation of child apps, which then synchronize the Kubernetes manifests.

### Validation & Monitoring
Verify real-time event-driven auditing:
```cmd
kubectl logs -f deployment/audit-service -n enterprise-lab
```

## Architecture & Monitoring Features

- **Event-Driven Flow**: Microservices publish events to a **RabbitMQ** fanout exchange. The **Audit Service** consumes these events and updates a **Redis** cache for real-time dashboard metrics.
- **Enterprise Dashboard**: Displays live audit logs, Redis cache health (memory usage/hit rates), and database metrics.
- **Architecture-as-Code**: The frontend renders `lab.md` directly for integrated documentation.
