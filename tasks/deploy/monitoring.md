@after deploy.md

Uptime, service load, disk space, postgres slow queries, site health, active
users. Needs external service for uptime (can't alert yourself if you're
down). Logs and slow queries need to surface somewhere visible.

Options:
- Grafana Cloud (free tier, Alloy agent on server)
- Datadog
- New Relic
- Better Stack
- Sentry (errors/performance)
- Honeycomb
- Uptime Robot (uptime only)
- healthchecks.io (cron/uptime)
- Papertrail (logs)
- Logtail (logs)
- Netdata (self-hosted, lightweight)
- Self-hosted Prometheus/Grafana

- [ ] investigate monitoring options
