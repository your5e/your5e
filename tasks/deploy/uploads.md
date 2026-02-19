@after release.md

File uploads need protection at the web layer, not just the application
layer, and probably rate limiting.

- [ ] setup proxy to reject oversized requests immediately
- [ ] rate limit upload endpoint
