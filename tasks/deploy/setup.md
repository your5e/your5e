@after ../build/setup.md

Docker Swarm on one node, enough to prove the ability to deploy without
interruptions. Secrets through `docker secret`, done manually.
Traefik as reverse proxy.

Terraform provisions infrastructure, CI creates tfplan artifact.
Ansible configures the server. Manually apply terraform and ansible.

- [ ] Terraform for VPS and DNS
- [ ] CI creates tfplan artifact
- [ ] Ansible configures Swarm, Traefik, Postgres
- [ ] script to apply and run ansible
