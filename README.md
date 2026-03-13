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
	rbac.yaml                  # Placeholder (currently empty)
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

### 1. Install Pulumi Operator

```bash
bash scripts/install_operator.sh
```

### 2. Apply base manifests

Current files are in `k8s/base/`, so apply them directly:

```bash
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/pulumi-stack.yaml
```

### 3. Enable Flux reconciliation

```bash
kubectl apply -f k8s/flux/gitrepository.yaml
kubectl apply -f k8s/flux/kustomization.yaml
```

Flux will watch this repository and reconcile `k8s/base` on the configured interval.

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

- `k8s/rbac.yaml` is present but empty.
- There is no root-level Pulumi `__main__.py`; this repo currently relies on the automation script and `pulumi_program/` directory pattern.

## Why This Repo Is Useful

This project is a good starting point for teams that want to:

- encapsulate Azure infrastructure in reusable Pulumi components,
- trigger deployments programmatically from Python (Automation API), and
- move toward cluster-driven GitOps reconciliation with Pulumi Operator + Flux.