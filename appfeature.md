# Enterprise Microservices Application Features & Architecture

This document provides a logical overview of the system features, their purpose, and the underlying data workflows.

## 🔹 1. High-Level Architecture
```text
[ USER BROWSER ]
       |
       v (NodePort 30005)
+-----------------------+      [ KUBERNETES API ]
|    FRONTEND SERVICE   | <--- (Cluster Intelligence)
+-----------------------+
       |
       +-----> [ AUTH SERVICES ] (Login, Logout, Register, Profile, Forgot Password)
       |           |
       |           +---> [ MYSQL DB ] (Persistent Storage)
       |
       +-----> [ EVENT BUS ] (RabbitMQ)
       |           |
       |           v
       |       [ AUDIT SERVICE ] (Consumer)
       |           |
       |           v
       +-----> [ CACHE/METRICS ] (Redis)
```

## 🔹 2. Core Features & Logical Workflows

### A. User Registration
**Purpose**: Allows new users to join the platform and initializes their profile.
**Workflow**:
1. [User] -> [Frontend]: Submits registration form.
2. [Frontend] -> [Register Service]: Forwards POST request with credentials.
3. [Register Service]: Hashes password and saves record to **MySQL**.
4. [Register Service] -> [RabbitMQ]: Publishes `user.register` event.
5. [Audit Service] -> [Redis]: Consumes event and stores it in `enterprise_audit_log` list.

### B. Enterprise Authentication (Login/Logout)
**Purpose**: Secure access to the command center and session management.
**Workflow**:
1. [User] -> [Frontend]: Enters credentials.
2. [Frontend] -> [Login Service]: Validates against **MySQL** hash.
3. [Login Service] -> [Redis]: Creates a session token with 1-hour expiry.
4. [Login Service] -> [RabbitMQ]: Publishes `user.login` event.
5. [User Browser]: Receives session cookie; Dashboard becomes accessible.

### C. Cluster Intelligence Dashboard
**Purpose**: Real-time monitoring of the underlying Kubernetes infrastructure.
**Workflow**:
1. [User] -> [Frontend]: Clicks "Cluster Overview" tab.
2. [Frontend] -> [Kubernetes API]: Uses `frontend-sa` (ServiceAccount) to list Pods and Nodes.
3. [K8s API]: Returns JSON metadata of all resources in `enterprise-lab` namespace.
4. [Frontend]: Renders live health badges (Running/Pending) for all containers.

### D. RBAC Management (Admin Console)
**Purpose**: Allows administrators to promote/demote users and manage permissions.
**Workflow**:
1. [Admin] -> [Frontend]: Clicks "User Management".
2. [Frontend] -> [Profile Service]: Fetches all user records from **MySQL**.
3. [Admin]: Clicks "Make Admin" on a user.
4. [Frontend] -> [Profile Service]: Sends update request to `/admin/update-role`.
5. [Profile Service]: Commits role change to **MySQL**.

### E. Live Audit Streaming
**Purpose**: Provides immediate visibility into system-wide activity.
**Workflow**:
1. [Frontend]: Opens a Server-Sent Events (SSE) connection to `/stream-logs`.
2. [Frontend] -> [Redis]: Continuously polls `enterprise_audit_log`.
3. [User UI]: Displays incoming RabbitMQ messages in a terminal-style view.

## 🔹 3. Secure Asset Downloads
- **Download Logs**: Fetches entire history from Redis, formats it into a text file, and streams it to the user.
- **Download Kubeconfig**: (Admin Only) Generates a pre-configured Kubernetes config file to allow developers to connect local tools to the cluster.
