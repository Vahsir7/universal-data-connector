@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

if /I "%MODE%"=="help" goto :usage
if /I "%MODE%"=="--help" goto :usage
if /I "%MODE%"=="-h" goto :usage

echo [INFO] Mode: %MODE%

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker CLI not found in PATH.
  exit /b 1
)

if /I "%MODE%"=="docker" goto :start_docker
if /I "%MODE%"=="k8s" goto :start_k8s
if /I "%MODE%"=="all" goto :start_all

echo [ERROR] Unknown mode: %MODE%
goto :usage

:start_all
call :start_docker
if errorlevel 1 exit /b 1
call :start_k8s
if errorlevel 1 exit /b 1
goto :done

:start_docker
echo [INFO] Starting Docker Compose stack...
docker compose up -d --build
if errorlevel 1 (
  echo [ERROR] Failed to start Docker Compose.
  exit /b 1
)
echo [OK] Docker Compose is up. API docs: http://localhost:8000/docs
exit /b 0

:start_k8s
echo [INFO] Starting Kubernetes deployment...

where kubectl >nul 2>nul
if errorlevel 1 (
  echo [ERROR] kubectl not found in PATH.
  exit /b 1
)

for /f %%I in ('docker image inspect udc-api:latest --format "{{.Id}}" 2^>nul') do set "IMAGE_ID=%%I"
if "%IMAGE_ID%"=="" (
  echo [INFO] Building Docker image udc-api:latest ...
  docker build -t udc-api:latest .
  if errorlevel 1 (
    echo [ERROR] Docker image build failed.
    exit /b 1
  )
)

where kind >nul 2>nul
if errorlevel 1 (
  echo [WARN] kind not found. Using current kubectl context.
) else (
  set "HAS_KIND_CLUSTER="
  for /f %%C in ('kind get clusters 2^>nul') do (
    if /I "%%C"=="kind" set "HAS_KIND_CLUSTER=1"
  )

  if not defined HAS_KIND_CLUSTER (
    echo [INFO] Creating kind cluster "kind" ...
    kind create cluster --name kind
    if errorlevel 1 (
      echo [ERROR] Failed to create kind cluster.
      exit /b 1
    )
  )

  kubectl config use-context kind-kind >nul 2>nul
  if errorlevel 1 (
    echo [WARN] Could not switch context to kind-kind. Continuing with current context.
  )

  echo [INFO] Loading image into kind cluster...
  kind load docker-image udc-api:latest --name kind
  if errorlevel 1 (
    echo [ERROR] Failed to load image into kind.
    exit /b 1
  )
)

echo [INFO] Applying Kubernetes manifests...
kubectl apply -k k8s
if errorlevel 1 (
  echo [ERROR] kubectl apply -k k8s failed.
  exit /b 1
)

kubectl apply -f k8s/secret.yaml
if errorlevel 1 (
  echo [ERROR] kubectl apply -f k8s/secret.yaml failed.
  exit /b 1
)

echo [INFO] Waiting for deployments to become ready...
kubectl -n udc rollout status deploy/udc-redis --timeout=180s
if errorlevel 1 exit /b 1
kubectl -n udc rollout status deploy/udc-api --timeout=180s
if errorlevel 1 exit /b 1

echo [OK] Kubernetes deployment is ready.
echo [INFO] Start local access with:
echo        kubectl -n udc port-forward svc/udc-api 8080:80
echo [INFO] Then open: http://localhost:8080/docs
exit /b 0

:done
echo [SUCCESS] Requested services are running.
exit /b 0

:usage
echo Usage: %~n0 [all^|docker^|k8s^|help]
echo.
echo   all    - start Docker Compose and Kubernetes deployment
echo   docker - start Docker Compose only
echo   k8s    - start Kubernetes deployment only
echo   help   - show this message
exit /b 1
