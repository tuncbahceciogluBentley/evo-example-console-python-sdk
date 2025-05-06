# Sample for Seequent EVO public Python SDK

## About uv
This project uses uv. 

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver, written in Rust. It's designed to be a drop-in replacement for pip and can significantly speed up Python package installation.

After installing uv use `uv run main.py` to run the script.

## Usage

This script provides a command-line interface to interact with Seequent EVO API. It requires a valid client ID to authenticate.

Basic syntax:
```
uv run main.py [MODE] --client-id YOUR_CLIENT_ID [OPTIONS]
```

### Modes (required, choose one):

- `--instances`: Show EVO instances for each organization
  ```
  uv run main.py --instances --client-id YOUR_CLIENT_ID
  ```

- `--workspaces`: Show workspaces for a specific organization and instance (hub) id.
  ```
  uv run main.py --workspaces --org-id ORGANIZATION_ID --instance-url INSTANCE_URL --client-id YOUR_CLIENT_ID
  ```

- `--files`: Show files for a specific workspace
  ```
  uv run main.py --files --workspace-id WORKSPACE_ID --instance-url INSTANCE_URL --org-id ORGANIZATION_ID --client-id YOUR_CLIENT_ID
  ```

- `--objects`: Show objects for a specific workspace
  ```
  uv run main.py --objects --workspace-id WORKSPACE_ID --instance-url INSTANCE_URL --org-id ORGANIZATION_ID --client-id YOUR_CLIENT_ID
  ```

## Client Id

A valid OAuth client ID is required to authenticate with the EVO API. This must be provided using the `--client-id` parameter.

To register a client ID, contact your Seequent EVO administrator or visit the Seequent Developer Portal.

