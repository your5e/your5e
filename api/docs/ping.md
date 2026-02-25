# Ping

Test your authentication works.

## GET /api/ping

Returns:

- `200 OK` on a valid token

    ```json
    {"username": "your-username"}
    ```

- `401 Unathorized` if the token is missing or invalid
