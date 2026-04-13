Move the API from `your5e.com/api/...` to `api.your5e.com/v1/...`.


# dev and testing @phase

Split Django settings into base, web, and api variants.
Create `settings/` package with `base.py`, `web.py`, `api.py` and corresponding
`urls/` package with `web.py`, `api.py`, set via `DJANGO_SETTINGS_MODULE`.

- [X] create separate API and website apps configs
        - use urlconf param to reverse for API responses including html links
        - dev-web on port 5843, dev-api 5844, test-web 5853, test-api 5854
- [X] update dev and test docker configurations
- [X] update the sync engines integration tests


# production @phase

Add `api` service to Swarm stack, using the same image as web.

- [ ] update terraform, `app-stack.yml`, and collectstatic
- [ ] update API docs
