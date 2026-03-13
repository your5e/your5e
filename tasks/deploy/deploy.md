@after setup.md

Set up automatic deploys from Github tags.

Migrations run in the container entrypoint before the app starts.

- [ ] build and push image on merge to main
- [ ] containrrr/shepherd deploys from `:latest`, tag to trigger deploy
- [ ] ensure rollbacks work on broken build and do not redeploy again immediately
