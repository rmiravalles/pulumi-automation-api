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
- Installs `azure-native` plugin version `v3.15.0`.
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

## CI/CD with GitHub Actions

This repository now includes a workflow at `.github/workflows/ci-cd.yml`.

### Setup the workflow in GitHub

1. Push this repository (including `.github/workflows/ci-cd.yml`) to GitHub.
2. Open the repository in GitHub and go to `Settings` -> `Secrets and variables` -> `Actions`.
3. Under `Repository secrets`, add all required secrets listed below.
4. Go to the `Actions` tab and confirm workflows are enabled for the repository.
5. Trigger CI by opening a pull request to `main`.
6. Trigger CD by merging/pushing to `main`.
7. Optionally trigger manually from `Actions` -> `CI-CD` -> `Run workflow`.

Verification:

- PR run should execute only the `Test` job.
- Push to `main` should execute `Test` and then `Deploy`.
- In a successful deploy run, you should see `Deploying stack...` in logs.

Behavior:

- On `pull_request` to `main`: run test job (`pytest`).
- On `push` to `main`: run tests, then deploy with `python automation/deploy.py`.
- Supports manual run via `workflow_dispatch`.

### Required GitHub repository secrets

Add these in `Settings` -> `Secrets and variables` -> `Actions`:

- `PULUMI_CONFIG_PASSPHRASE`: passphrase used by the stack secrets manager.
- `PULUMI_BACKEND_URL`: backend URL (for example `azblob://state`).
- `AZURE_STORAGE_ACCOUNT`: storage account used by the Azure Blob Pulumi backend.
- `AZURE_STORAGE_KEY`: storage key for that account.
- `ARM_CLIENT_ID`: Azure service principal client ID.
- `ARM_CLIENT_SECRET`: Azure service principal client secret.
- `ARM_TENANT_ID`: Azure tenant ID.
- `ARM_SUBSCRIPTION_ID`: Azure subscription ID.

Where to get Azure values:

- `ARM_SUBSCRIPTION_ID`: Azure Portal -> `Subscriptions` -> `<your subscription>` -> `Subscription ID`.
- `ARM_TENANT_ID`: Azure Portal -> `Microsoft Entra ID` -> `Overview` -> `Tenant ID`.
- `ARM_CLIENT_ID`: Azure Portal -> `Microsoft Entra ID` -> `App registrations` -> `<your app>` -> `Application (client) ID`.
- `ARM_CLIENT_SECRET`: Azure Portal -> `App registrations` -> `<your app>` -> `Certificates & secrets` -> create a new client secret and copy `Value`.

If you are not using an Azure Blob backend, you can omit `PULUMI_BACKEND_URL`, `AZURE_STORAGE_ACCOUNT`, and `AZURE_STORAGE_KEY`, and use your preferred Pulumi backend login strategy.

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

### Troubleshooting Local Deployment

If first run fails with `no stack named 'dev' found`, that part is expected while Pulumi tries to create the stack.

If it then fails with `passphrase must be set`, configure one of the following before running `python automation/deploy.py`:

```bash
export PULUMI_CONFIG_PASSPHRASE='<your-strong-passphrase>'
```

Or use a file-based passphrase:

```bash
printf '%s' '<your-strong-passphrase>' > ~/.pulumi-passphrase
chmod 600 ~/.pulumi-passphrase
export PULUMI_CONFIG_PASSPHRASE_FILE=~/.pulumi-passphrase
```

Notes:

- Keep the same passphrase for future runs so Pulumi can decrypt stack secrets.
- If you are using an Azure Blob backend (`azblob://...`), also ensure backend variables are set (for example `AZURE_STORAGE_ACCOUNT` and either `AZURE_STORAGE_KEY` or `AZURE_STORAGE_SAS_TOKEN`).

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

If you have already applied this repo's Flux manifests (`k8s/flux/*.yaml`), use:

```bash
flux reconcile source git azure-pulumi-platform -n flux-system
flux reconcile kustomization pulumi-platform -n flux-system
```

If you only ran `flux bootstrap github` and did not apply `k8s/flux/*.yaml` yet, the default object names are `flux-system`:

```bash
flux reconcile source git flux-system -n flux-system
flux reconcile kustomization flux-system -n flux-system
```

To switch to this repository's custom names (`azure-pulumi-platform` / `pulumi-platform`), apply:

```bash
kubectl apply -f k8s/flux/gitrepository.yaml
kubectl apply -f k8s/flux/kustomization.yaml
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
- Troubleshooting: if you get `gitrepositories.source.toolkit.fluxcd.io "azure-pulumi-platform" not found`, run `flux get sources git -n flux-system` and use the name that exists, or apply `k8s/flux/*.yaml` first.

## Configuration

Current config files:

- `pulumi.yaml`
- `pulumi.dev.yaml`

Important detail:

- `pulumi_program/__main__.py` reads `azure-native:location`.
- `automation/deploy.py` and `pulumi.dev.yaml` set `azure-native:location`.

This keeps local Automation API and stack configuration consistent.

## Setting the state backend

```bash



# 1) Set backend storage account info
export AZURE_STORAGE_ACCOUNT=<your-storage-account-name>
export AZURE_STORAGE_KEY=$(az storage account keys list --account-name $AZURE_STORAGE_ACCOUNT --query '[0].value' -o tsv)
# (or use AZURE_STORAGE_SAS_TOKEN instead of key)

# 2) Ensure backend is selected
pulumi login azblob://state

# 3) Verify backend is reachable
pulumi whoami

# 4) Run deploy from repo root
cd /home/rodrigo/Repos/pulumi-automation-api
python automation/deploy.py
```

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