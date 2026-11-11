"""
Fabric CI/CD Deployment Script
===============================
Deploys Fabric items (SemanticModel, Report) to a target workspace using the
fabric-cicd library. Environment-specific values are substituted via parameter.yml.

Usage (from repo root):
    python .deploy/fabric_workspace.py

The script determines workspace_id and environment from either:
  1. CLI arguments   (--workspace_id, --environment, --tenant_id, --client_id, --client_secret)
  2. Environment variables (FABRIC_WORKSPACE_ID, ENVIRONMENT, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)

Docs:
  - fabric-cicd:  https://microsoft.github.io/fabric-cicd/latest/
  - Auth:         https://microsoft.github.io/fabric-cicd/latest/example/authentication/
  - Params:       https://microsoft.github.io/fabric-cicd/latest/how_to/parameterization/
"""

import argparse
import os
import sys
from pathlib import Path

from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items


def main():
    parser = argparse.ArgumentParser(description="Deploy Fabric workspace items with fabric-cicd")
    parser.add_argument("--workspace_id", type=str, default=os.environ.get("FABRIC_WORKSPACE_ID"))
    parser.add_argument("--environment", type=str, default=os.environ.get("ENVIRONMENT"))
    parser.add_argument("--tenant_id", type=str, default=os.environ.get("AZURE_TENANT_ID"))
    parser.add_argument("--client_id", type=str, default=os.environ.get("AZURE_CLIENT_ID"))
    parser.add_argument("--client_secret", type=str, default=os.environ.get("AZURE_CLIENT_SECRET"))
    args = parser.parse_args()

    # --- Validate required inputs -------------------------------------------
    if not args.workspace_id:
        sys.exit("ERROR: workspace_id is required (--workspace_id or FABRIC_WORKSPACE_ID env var)")
    if not args.environment:
        sys.exit("ERROR: environment is required (--environment or ENVIRONMENT env var)")

    # --- Repository directory is the project root (one level up from .deploy/) ---
    repository_directory = str(Path(__file__).resolve().parent.parent)

    # Items to deploy — Report + SemanticModel for this Power BI project
    item_type_in_scope = ["SemanticModel", "Report"]

    # --- Authentication ------------------------------------------------------
    # If SPN credentials are provided, use explicit ClientSecretCredential.
    # Otherwise, fall back to DefaultAzureCredential (works with az login,
    # AzureCLI task in Azure DevOps, or azure/login in GitHub Actions).
    token_credential = None
    if args.client_id and args.client_secret and args.tenant_id:
        from azure.identity import ClientSecretCredential
        token_credential = ClientSecretCredential(
            client_id=args.client_id,
            client_secret=args.client_secret,
            tenant_id=args.tenant_id,
        )

    # --- Build FabricWorkspace -----------------------------------------------
    ws_kwargs = {
        "workspace_id": args.workspace_id,
        "environment": args.environment,
        "repository_directory": repository_directory,
        "item_type_in_scope": item_type_in_scope,
    }
    if token_credential:
        ws_kwargs["token_credential"] = token_credential

    print(f"Deploying to workspace {args.workspace_id} (environment={args.environment})")
    print(f"Repository directory: {repository_directory}")
    print(f"Items in scope: {item_type_in_scope}")

    target_workspace = FabricWorkspace(**ws_kwargs)

    # --- Deploy --------------------------------------------------------------
    publish_all_items(target_workspace)
    unpublish_all_orphan_items(target_workspace)
    print("Deployment complete.")


if __name__ == "__main__":
    main()
