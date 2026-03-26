@after ../build/setup.md

Docker Swarm on one node, enough to prove the ability to deploy without
interruptions. Secrets through `docker secret`, automated in Ansible.
Traefik as reverse proxy.

Terraform provisions infrastructure, CI creates tfplan artifact.
Ansible configures the server. Manually apply terraform and ansible.

- [X] Terraform for VPS
- [ ] Remote backend for Terraform state
- [ ] CI creates tfplan artifact
- [X] Ansible configures Swarm, Traefik, Postgres
- [ ] Generate Ansible inventory from Terraform output
- [X] script to apply and run ansible
