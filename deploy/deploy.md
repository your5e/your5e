# Deployment

Single-node Docker Swarm on Hetzner Cloud, with Traefik reverse proxy and
Let's Encrypt certificates.

## Architecture

| Service  | Stack Definition                    | Ansible Task                 |
| -------- | ----------------------------------- | ---------------------------- |
| Traefik  | `ansible/files/traefik-stack.yml`   | `ansible/tasks/traefik.yml`  |
| Postgres | `ansible/files/postgres-stack.yml`  | `ansible/tasks/postgres.yml` |
| App      | `ansible/files/app-stack.yml`       | `ansible/tasks/app.yml`      |

The app stack contains two services: `web` (your5e.com) and `api` (api.your5e.com).

The app image is built from `Dockerfile` and published to
`ghcr.io/your5e/your5e:latest`.

## Deploying changes

The GitHub workflow (`.github/workflows/build.yml`) automatically builds and
pushes the image when tests pass on main.

```bash
# manually build the docker image, if necessary
(computer)% make build deploy

# deploy the image tagged 'latest'
(computer)% make deploy
```

## Rebuilding from scratch

### Prerequisites

Accounts:
- Hetzner Cloud account with API token
- GitHub account with PAT (write:packages scope)
- Domain with nameservers pointed to Hetzner

Tools:
- terraform (`brew install hashicorp/tap/terraform`)
- ansible (`pipx install ansible`)
- docker

### 1. Terraform

Create `terraform/terraform.tfvars`:

```hcl
hcloud_token   = "your-hetzner-api-token"
ssh_public_key = "ssh-ed25519 AAAA... user@host"
```

If using 1Password SSH agent, get your public key with `ssh-add -L`.

```bash
make tf-plan    # review changes
make tf-apply   # create VPS and DNS zone
```

Update nameservers at your registrar to those output by terraform.

### 2. Bootstrap

Run once as root on fresh server:

```bash
make ansible-bootstrap
```

This creates the admin user, hardens SSH, and sets up passwordless sudo.
After this, root SSH is disabled.

### 3. OS setup

```bash
make ansible-os
```

This installs Docker, initialises Swarm, and creates overlay networks.

### 4. App setup

```bash
make ansible-app
```

This creates secrets (if missing), deploys Traefik, Postgres, and the app services.

### 5. Build and push the app image

```bash
echo TOKEN | docker login ghcr.io -u USERNAME --password-stdin
make deploy
```

## Destroying everything

```bash
cd terraform && terraform destroy
```

This removes the VPS and DNS zone. The Hetzner API token and GitHub PAT remain.
