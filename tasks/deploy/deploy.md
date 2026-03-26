@after setup.md

Set up automatic deploys from Github tags.

Migrations run as a one-shot container before the service update.

- [X] build and push image on merge to main
- [ ] containrrr/shepherd deploys from `:latest`, tag to trigger deploy
- [ ] ensure rollbacks work on broken build and do not redeploy again immediately
