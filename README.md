# Pulumi Automation API Azure Platform Example

This repository is a Python-based infrastructure project that demonstrates two ways to manage Azure resources with Pulumi:

1. Pulumi Automation API from a Python script.
2. GitOps-style reconciliation using the Pulumi Kubernetes Operator and Flux manifests.

The project provisions a small Azure baseline (Resource Group + Storage Account) through a reusable Pulumi component, and includes Kubernetes manifests to run that same Pulumi program inside a cluster.

## What This Repository Does

At a high level:

1. Defines an `AzurePlatform` component in `components/azure_platform.py`.
2. Uses that component in `pulumi_program/__main__.py` to create:
	 - an Azure Resource Group
	 - an Azure Storage Account
3. Exposes an Automation API entrypoint in `automation/deploy.py` that creates/selects a stack and runs `stack.up()`.
4. Provides Kubernetes manifests in `k8s/` for Pulumi Operator + Flux workflows.

## Architecture

### Core Pulumi Component

`components/azure_platform.py`

- Implements `AzurePlatform` as a `pulumi.ComponentResource`.
- Creates:
	- `azure.resources.ResourceGroup` named `<name>-rg`
	- `azure.storage.StorageAccount` named `<name>storage`
- Registers output `resourceGroup`.

### Pulumi Program

`pulumi_program/__main__.py`

- Reads `azure-native:location`.
- Falls back to `westeurope` if not set.
- Instantiates `AzurePlatform("demo-platform", location=...)`.
- Exports `platformName`.

### Automation API Driver

`automation/deploy.py`

- Uses `pulumi.automation.create_or_select_stack`.
- Stack name: `dev`.
- Project name: `azure-automation-api` (matches `pulumi.yaml`).
- Program callback imports `pulumi_program.__main__`.
- Installs `azure-native` plugin version `v2.0.0`.
- Sets config `azure-native:location=westeurope`.
- Runs `stack.up()` and streams output.

## Repository Layout

```text
automation/
	deploy.py                  # Automation API deployment entrypoint
components/
	azure_platform.py          # Reusable Pulumi component (RG + Storage)
k8s/
	base/
		namespace.yaml           # Namespace for Pulumi resources in cluster
		pulumi-stack.yaml        # Pulumi Operator Stack CR
	flux/
		gitrepository.yaml       # Flux source definition
		kustomization.yaml       # Flux reconciliation definition
	rbac.yaml                  # SA/Role/RoleBinding for Stack runner
pulumi_program/
	__main__.py                # Pulumi program used by Automation and Operator
scripts/
	install_operator.sh        # Installs Pulumi Kubernetes Operator
	deploy.sh                  # Applies Pulumi Stack base manifests
tests/
	test_component.py          # Basic component instantiation test
```

## Prerequisites

- Python 3.10+
- Azure credentials configured (for real deployments)
- Pulumi CLI
- `pip`
- Optional for GitOps path:
	- Kubernetes cluster
	- `kubectl`
	- Flux installed in cluster

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local Deployment (Automation API)

Run the Python automation driver:

```bash
python automation/deploy.py
```

What this does:

1. Creates or selects stack `dev`.
2. Installs Pulumi Azure Native plugin.
3. Sets stack config.
4. Executes deployment.

## GitOps / Kubernetes Operator Workflow

Run these commands in this exact order from the repository root:

```bash
# 0) Optional: activate virtual environment
source .venv/bin/activate

# 1) Install Pulumi Kubernetes Operator
bash scripts/install_operator.sh

# 2) Create namespace for Stack resources
kubectl apply -f k8s/base/namespace.yaml

# 3) Apply RBAC for the Stack runner service account
kubectl apply -f k8s/rbac.yaml

# 4) Apply the Pulumi Stack custom resource
kubectl apply -f k8s/base/pulumi-stack.yaml

# 5) (Optional) Enable Flux reconciliation
kubectl apply -f k8s/flux/gitrepository.yaml
kubectl apply -f k8s/flux/kustomization.yaml
```

Before step 4, make sure `k8s/base/pulumi-stack.yaml` includes these fields:

```yaml
metadata:
	namespace: pulumi-system
spec:
	serviceAccountName: pulumi-stack-sa
```

If Flux is enabled, it will watch this repository and reconcile `k8s/base` on the configured interval.

Quick verification:

```bash
kubectl get sa,role,rolebinding -n pulumi-system
kubectl get stacks -n pulumi-system
kubectl get pods -n pulumi-kubernetes-operator
```

## Bootstrap This Repository with FluxCD

Use this flow when setting up Flux on a fresh cluster and wiring it to this repository.

Prerequisites:

- `flux` CLI installed
- `kubectl` configured to the target cluster
- GitHub personal access token with repo admin/write permissions

### 1. Verify cluster access

```bash
kubectl get nodes
```

### 2. Export GitHub credentials for bootstrap

```bash
export GITHUB_TOKEN=<your-github-pat>
export GITHUB_USER=rmiravalles
```

### 3. Bootstrap Flux controllers and Git source

```bash
flux bootstrap github \
	--owner=$GITHUB_USER \
	--repository=pulumi-automation-api \
	--branch=main \
	--path=./k8s/flux \
	--personal
```

This installs Flux in `flux-system` and commits/uses manifests from `k8s/flux`.

### 4. Confirm Flux health

```bash
flux check
flux get sources git -n flux-system
flux get kustomizations -n flux-system
```

### 5. Reconcile immediately (optional)

```bash
flux reconcile source git azure-pulumi-platform -n flux-system
flux reconcile kustomization pulumi-platform -n flux-system
```

### 6. Confirm Pulumi resources were applied

```bash
kubectl get namespace pulumi-system
kubectl get stacks -n pulumi-system
```

Notes:

- `k8s/flux/gitrepository.yaml` points to `https://github.com/rmiravalles/pulumi-automation-api` on `main`.
- `k8s/flux/kustomization.yaml` reconciles `./k8s/base` into `pulumi-system`.
- Keep `k8s/rbac.yaml` and `k8s/base/pulumi-stack.yaml` valid, because Flux will continuously apply those manifests.

## Configuration

Current config files:

- `pulumi.yaml`
- `pulumi.dev.yaml`

Important detail:

- `pulumi_program/__main__.py` reads `azure-native:location`.
- `automation/deploy.py` and `pulumi.dev.yaml` set `azure-native:location`.

This keeps local Automation API and stack configuration consistent.

## Testing

Run tests with:

```bash
./.venv/bin/python -m pytest
```

If your shell is already inside the virtualenv, `pytest` also works.

Current test coverage is minimal and only checks component instantiation.

## Current State and Limitations

- RBAC for the Stack runner must exist in `k8s/rbac.yaml` before applying `k8s/base/pulumi-stack.yaml`.
- There is no root-level Pulumi `__main__.py`; this repo currently relies on the automation script and `pulumi_program/` directory pattern.

## Why This Repo Is Useful

This project is a good starting point for teams that want to:

- encapsulate Azure infrastructure in reusable Pulumi components,
- trigger deployments programmatically from Python (Automation API), and
- move toward cluster-driven GitOps reconciliation with Pulumi Operator + Flux.