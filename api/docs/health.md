# Health

Check if the API is healthy. Used by container orchestration for health checks.
Does not require authentication.

## GET /v1/health

Returns:

- `200 OK` when the API and database are healthy

    ```json
    {"status": "ok"}
    ```

- `503 Service Unavailable` when the database is unreachable

    ```json
    {"status": "error"}
    ```
