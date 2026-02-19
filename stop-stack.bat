@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

if /I "%MODE%"=="help" goto :usage
if /I "%MODE%"=="--help" goto :usage
if /I "%MODE%"=="-h" goto :usage

echo [INFO] Mode: %MODE%

if /I "%MODE%"=="docker" goto :stop_docker
if /I "%MODE%"=="k8s" goto :stop_k8s
if /I "%MODE%"=="all" goto :stop_all
if /I "%MODE%"=="kind-delete" goto :delete_kind

echo [ERROR] Unknown mode: %MODE%
goto :usage

:stop_all
call :stop_docker
call :stop_k8s
goto :done

:stop_docker
where docker >nul 2>nul
if errorlevel 1 (
  echo [WARN] Docker CLI not found. Skipping Docker shutdown.
  exit /b 0
)

echo [INFO] Stopping Docker Compose stack...
docker compose down
if errorlevel 1 (
  echo [WARN] Docker Compose down returned non-zero. Continuing.
) else (
  echo [OK] Docker Compose stopped.
)
exit /b 0

:stop_k8s
where kubectl >nul 2>nul
if errorlevel 1 (
  echo [WARN] kubectl not found. Skipping Kubernetes shutdown.
  exit /b 0
)

echo [INFO] Removing Kubernetes resources from k8s/ ...
kubectl delete -k k8s --ignore-not-found=true
if errorlevel 1 (
  echo [WARN] kubectl delete -k k8s returned non-zero. Continuing.
) else (
  echo [OK] Kubernetes resources removed.
)

echo [INFO] Attempting to delete secret k8s/secret.yaml if present...
kubectl delete -f k8s/secret.yaml --ignore-not-found=true >nul 2>nul

echo [INFO] Namespace status:
kubectl get ns udc >nul 2>nul
if errorlevel 1 (
  echo [OK] Namespace udc not found (already deleted or never created).
) else (
  echo [INFO] Namespace udc still exists (may be terminating or reused).
)
exit /b 0

:delete_kind
where kind >nul 2>nul
if errorlevel 1 (
  echo [WARN] kind not found. Nothing to delete.
  exit /b 0
)

echo [INFO] Deleting kind cluster "kind" ...
kind delete cluster --name kind
if errorlevel 1 (
  echo [WARN] Failed to delete kind cluster or it does not exist.
) else (
  echo [OK] kind cluster deleted.
)
exit /b 0

:done
echo [SUCCESS] Stop operations completed.
echo [TIP] To also remove the kind cluster, run: %~n0 kind-delete
exit /b 0

:usage
echo Usage: %~n0 [all^|docker^|k8s^|kind-delete^|help]
echo.
echo   all         - stop Docker Compose and delete Kubernetes resources
echo   docker      - stop Docker Compose only
echo   k8s         - delete Kubernetes resources only
echo   kind-delete - delete kind cluster named "kind"
echo   help        - show this message
exit /b 1
