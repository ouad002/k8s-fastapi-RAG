# Docker & Kubernetes DevOps Cheatsheet

Built from the `k8s-fastapi` project (FastAPI, Docker, kind, GitHub Actions) plus the commands used daily in DevOps and infrastructure work.

---

## 1. Docker

### Images
```bash
docker build -t k8s-fastapi:v1 .              # build image from ./Dockerfile
docker build -f Dockerfile.prod -t app:prod . # use a specific Dockerfile
docker build --no-cache -t app:v1 .           # ignore layer cache
docker images                                 # list local images
docker image ls --filter dangling=true        # untagged leftovers
docker tag app:v1 ghcr.io/USER/app:v1         # add another name
docker rmi app:v1                             # delete image
docker history app:v1                         # show layers and sizes
docker inspect app:v1                         # full metadata (JSON)
docker save app:v1 -o app.tar                 # export to file
docker load -i app.tar                        # import from file
```

### Containers
```bash
docker run -d -p 8000:8000 --name api app:v1  # run detached, map port host:container
docker run --rm -it app:v1 sh                 # interactive, auto-delete on exit
docker run -e KEY=value app:v1                # environment variable
docker run --env-file .env app:v1             # variables from file
docker run -v $(pwd)/data:/data app:v1        # bind mount
docker run --memory=256m --cpus=0.5 app:v1    # resource limits
docker ps                                     # running containers
docker ps -a                                  # include stopped
docker logs api                               # show logs
docker logs -f --tail 50 api                  # follow last 50 lines
docker exec -it api sh                        # shell in running container
docker stop api && docker rm api              # stop and remove
docker rm -f api                              # force remove
docker stats                                  # live CPU/memory
docker cp api:/app/file.txt .                 # copy file out
```

### Registry
```bash
docker login ghcr.io -u USER                  # log in (use a token as password)
docker push ghcr.io/USER/app:v1               # upload image
docker pull ghcr.io/USER/app:v1               # download image
```

### Networks, volumes, cleanup
```bash
docker network ls
docker network create mynet
docker volume ls
docker volume create mydata
docker system df                              # disk usage
docker system prune                           # remove unused data
docker system prune -a --volumes              # aggressive cleanup (careful)
```

### Docker Compose
```bash
docker compose up -d                          # start services
docker compose up -d --build                  # rebuild then start
docker compose ps
docker compose logs -f service
docker compose down                           # stop and remove
docker compose down -v                        # also remove volumes
```

### Dockerfile essentials
```dockerfile
FROM python:3.12-slim          # base image
WORKDIR /app                   # working directory
COPY requirements.txt .        # copy dependency list first (better caching)
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                       # copy the code
EXPOSE 8000                    # documentation only, does not publish
ENV PORT=8000
USER 1000                      # do not run as root
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Best practices:
- Use small base images (`-slim`, `alpine`) and pin versions.
- Copy dependency files before code so the cache is reused.
- Use a `.dockerignore` (`.git`, `__pycache__`, `.venv`, `.env`).
- Run as a non-root user.
- Use multi-stage builds to keep build tools out of the final image.
- Bind to `0.0.0.0` inside containers, not `127.0.0.1`.

Multi-stage example:
```dockerfile
FROM python:3.12 AS build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim
COPY --from=build /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*
COPY . /app
```

---

## 2. kind (Kubernetes in Docker)

```bash
kind create cluster --name dev                # create cluster
kind create cluster --config kind-config.yaml # with config (ports, multi-node)
kind get clusters
kind delete cluster --name dev
kind load docker-image app:v1 --name dev      # copy local image into the nodes
kubectl cluster-info --context kind-dev
```

kind nodes cannot see your local Docker images, so load them with `kind load docker-image`. If the manifest uses `imagePullPolicy: Never`, the tag in the manifest must match the loaded tag exactly.

---

## 3. kubectl basics

### Context and cluster
```bash
kubectl config get-contexts
kubectl config use-context kind-dev
kubectl config set-context --current --namespace=myns
kubectl cluster-info
kubectl get nodes -o wide
kubectl version
```

### Get and describe
```bash
kubectl get pods                              # list pods
kubectl get pods -o wide                      # with node and IP
kubectl get pods -A                           # all namespaces
kubectl get pods -w                           # watch live
kubectl get pods -l app=fastapi               # filter by label
kubectl get all                               # pods, services, deployments, replicasets
kubectl get deploy,svc,ing,cm,secret
kubectl get pod NAME -o yaml                  # full YAML
kubectl get pod NAME -o jsonpath='{.status.phase}'
kubectl describe pod NAME                     # details and events (first stop for debugging)
kubectl describe deployment fastapi
kubectl api-resources                         # list resource types
kubectl explain deployment.spec.strategy      # built-in docs
```

### Apply and delete
```bash
kubectl apply -f k8s/                         # create or update from folder
kubectl apply -f deployment.yaml
kubectl apply -k overlays/prod                # Kustomize
kubectl diff -f k8s/                          # preview changes
kubectl delete -f k8s/
kubectl delete pod NAME
kubectl delete pod NAME --force --grace-period=0   # last resort
kubectl create deployment web --image=nginx --dry-run=client -o yaml   # generate YAML
```

### Logs and exec
```bash
kubectl logs deployment/fastapi
kubectl logs POD -f --tail=100
kubectl logs POD -c CONTAINER                 # multi-container pod
kubectl logs POD --previous                   # logs of crashed container
kubectl exec -it POD -- sh
kubectl exec POD -- env
kubectl cp POD:/path/file ./file
```

### Access without exposing
```bash
kubectl port-forward service/fastapi 8000:8000
kubectl port-forward pod/POD 8000:8000
kubectl proxy                                 # API proxy on localhost:8001
```

### Scale, rollout, update
```bash
kubectl scale deployment/fastapi --replicas=3
kubectl set image deployment/fastapi fastapi=app:v2
kubectl rollout status deployment/fastapi --timeout=120s
kubectl rollout history deployment/fastapi
kubectl rollout undo deployment/fastapi       # roll back
kubectl rollout restart deployment/fastapi    # restart pods
kubectl rollout pause deployment/fastapi
kubectl autoscale deployment fastapi --min=2 --max=10 --cpu-percent=70
```

### Edit and label
```bash
kubectl edit deployment fastapi
kubectl label pod NAME env=dev
kubectl annotate pod NAME note="test"
kubectl patch deployment fastapi -p '{"spec":{"replicas":2}}'
kubectl set env deployment/fastapi KEY=value
```

### Resource usage
```bash
kubectl top nodes                             # needs metrics-server
kubectl top pods
kubectl get events --sort-by=.lastTimestamp
```

---

## 4. Kubernetes objects and YAML

| Object | Purpose |
|---|---|
| Pod | Smallest unit; one or more containers sharing network and storage |
| ReplicaSet | Keeps N identical pods running |
| Deployment | Manages ReplicaSets; rolling updates and rollbacks |
| StatefulSet | Pods with stable identity and storage (databases) |
| DaemonSet | One pod per node (log agents, monitoring) |
| Job / CronJob | One-off or scheduled tasks |
| Service | Stable network name and IP for a set of pods |
| Ingress | HTTP routing from outside to Services |
| ConfigMap | Non-secret configuration |
| Secret | Sensitive values (base64-encoded, not encrypted by default) |
| PersistentVolume / PVC | Storage and requests for storage |
| Namespace | Logical isolation within a cluster |
| ServiceAccount / Role / RoleBinding | Identity and permissions (RBAC) |
| HorizontalPodAutoscaler | Scales replicas by metrics |
| NetworkPolicy | Controls pod-to-pod traffic |

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi
  labels:
    app: fastapi
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fastapi            # must match the pod template labels
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      containers:
        - name: fastapi
          image: docker.io/library/k8s-fastapi:v1
          imagePullPolicy: Never      # local kind images only
          ports:
            - containerPort: 8000
          env:
            - name: APP_ENV
              value: "dev"
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 3
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi
spec:
  type: ClusterIP            # ClusterIP | NodePort | LoadBalancer
  selector:
    app: fastapi             # must match pod labels
  ports:
    - port: 8000             # Service port
      targetPort: 8000       # container port
```

### ConfigMap and Secret
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: info
***
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
stringData:
  password: change-me
```

### Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi
spec:
  rules:
    - host: api.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fastapi
                port:
                  number: 8000
```

### CronJob
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cleanup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: cleanup
              image: busybox
              command: ["sh", "-c", "echo cleaning"]
```

### HorizontalPodAutoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### PersistentVolumeClaim
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
```

---

## 5. Debugging playbook

| Symptom | Likely cause | First commands |
|---|---|---|
| `ImagePullBackOff` / `ErrImagePull` | Wrong image name or registry auth | `kubectl describe pod`, check image tag |
| `ErrImageNeverPull` | Image not loaded into kind | `kind load docker-image ...` |
| `CrashLoopBackOff` | App crashes at startup | `kubectl logs POD --previous` |
| `Pending` | No resources or unbound PVC | `kubectl describe pod`, check Events |
| Running but `0/1 READY` | Readiness probe failing | Check probe path and port, `kubectl logs` |
| Service gives no response | Selector or port mismatch | `kubectl get endpoints SERVICE` |
| `OOMKilled` | Memory limit too low | `kubectl describe pod`, raise limits |
| Changes not applied | Forgot to reapply or image tag cached | `kubectl rollout restart`, use unique tags |

Debug flow:
```bash
kubectl get pods
kubectl describe pod POD          # read the Events section at the bottom
kubectl logs POD --previous
kubectl get endpoints fastapi     # empty means selector mismatch
kubectl run tmp --rm -it --image=busybox -- sh   # test DNS and connectivity inside the cluster
```

---

## 6. Helm

```bash
helm repo add bitnami [https://charts.bitnami.com/bitnami](https://charts.bitnami.com/bitnami)
helm repo update
helm search repo nginx
helm install web bitnami/nginx -n web --create-namespace
helm install web ./chart -f values.yaml --set image.tag=v2
helm upgrade --install web ./chart -n web
helm list -A
helm status web -n web
helm get values web
helm template web ./chart                     # render without installing
helm lint ./chart
helm rollback web 1
helm uninstall web -n web
helm create mychart                           # scaffold a chart
```

---

## 7. Kustomize

```bash
kubectl kustomize overlays/prod               # render
kubectl apply -k overlays/prod                # apply
```

```yaml
# kustomization.yaml
resources:
  - deployment.yaml
  - service.yaml
images:
  - name: k8s-fastapi
    newTag: v2
namespace: prod
```

---

## 8. GitHub Actions

### Workflow used in this project
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - run: docker build -t k8s-fastapi:ci .
      - run: docker run -d -p 8000:8000 --name api k8s-fastapi:ci
      - run: |
          for i in $(seq 1 15); do curl -fsS http://localhost:8000/health && break; sleep 2; done
          curl -fsS http://localhost:8000/ready
      - if: failure()
        run: docker logs api
      - if: always()
        run: docker rm -f api

  k8s-test:
    needs: build-and-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: helm/kind-action@v1
        with:
          cluster_name: ci
      - run: docker build -t docker.io/library/k8s-fastapi:v1 .
      - run: kind load docker-image docker.io/library/k8s-fastapi:v1 --name ci
      - run: kubectl apply -f k8s/
      - run: kubectl rollout status deployment/fastapi --timeout=120s
      - if: failure()
        run: |
          kubectl get all
          kubectl describe pods
```

### Key concepts
| Keyword | Meaning |
|---|---|
| `on` | Events that trigger the workflow |
| `jobs.<id>.runs-on` | Runner (fresh VM per job) |
| `needs` | Run after another job, skip if it fails |
| `steps` | Sequence of `uses` (actions) and `run` (shell) |
| `if: failure()` / `always()` | Conditional steps |
| `env` / `secrets.NAME` | Variables and secrets |
| `environment: production` | Enables approvals and environment secrets |
| `permissions` | Limit the token's rights (least privilege) |

### Push image to GHCR (next step)
```yaml
permissions:
  contents: read
  packages: write
steps:
  - uses: actions/checkout@v6
  - uses: docker/login-action@v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}
  - uses: docker/build-push-action@v6
    with:
      context: .
      push: true
      tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

### CLI helpers
```bash
gh run list
gh run watch
gh run view --log-failed
gh run rerun --failed
```

---

## 9. Argo CD (GitOps)

```bash
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts \
  -f [https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml](https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml)
kubectl port-forward svc/argocd-server -n argocd 8080:443
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: fastapi
  namespace: argocd
spec:
  project: default
  source:
    repoURL: [https://github.com/USER/k8s-fastapi](https://github.com/USER/k8s-fastapi)
    targetRevision: main
    path: k8s
  destination:
    server: [https://kubernetes.default.svc](https://kubernetes.default.svc)
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

Flow: GitHub Actions (CI: build, test, push image, update tag in Git) then Argo CD (CD: pulls from Git and syncs the cluster).

---

## 10. Security and production habits

- Never commit secrets; use Kubernetes Secrets, GitHub secrets, or a vault. Prefer OIDC over long-lived cloud keys.
- Pin image tags (commit SHA or version), avoid `latest`.
- Set resource `requests` and `limits` on every container.
- Add readiness and liveness probes.
- Run as non-root; set `securityContext` (`runAsNonRoot`, `readOnlyRootFilesystem`).
- Scan images (Trivy, Grype) in CI.
- Use namespaces and RBAC with least privilege.
- Avoid self-hosted runners on public repositories.
- Build once, promote the same image through environments.

```bash
trivy image app:v1                            # vulnerability scan
kubectl auth can-i create pods --as=system:serviceaccount:default:sa
```

---

## 11. Linux and networking quick tools

```bash
curl -fsS http://localhost:8000/health        # fail on HTTP errors, silent but show errors
curl -I URL                                   # headers only
ss -tulpn                                     # listening ports
lsof -i :8000                                 # who uses a port
dig example.com / nslookup example.com        # DNS
journalctl -u SERVICE -f                      # systemd logs
df -h ; free -h ; top                         # disk, memory, CPU
tail -f file.log
grep -rn "text" .
jq '.items[].metadata.name'                   # parse JSON
```

---

## 12. Useful aliases

```bash
alias k=kubectl
alias kgp='kubectl get pods'
alias kd='kubectl describe'
alias kl='kubectl logs'
alias kaf='kubectl apply -f'
source <(kubectl completion bash)
complete -o default -F __start_kubectl k
```

---

## 13. Project command flow (this project)

```bash
# 1. Build and load into kind
docker build -t docker.io/library/k8s-fastapi:v1 .
kind load docker-image docker.io/library/k8s-fastapi:v1 --name dev

# 2. Deploy
kubectl apply -f k8s/
kubectl rollout status deployment/fastapi

# 3. Access
kubectl port-forward service/fastapi 8000:8000
curl http://localhost:8000/health

# 4. Iterate
git add . && git commit -m "change" && git push    # triggers CI
```