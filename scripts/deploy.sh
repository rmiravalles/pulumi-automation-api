#!/bin/bash

set -e

kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/pulumi-stack.yaml