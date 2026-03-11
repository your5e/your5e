# Ping

Test your authentication works.

## GET /api/ping

Returns:

- `200 OK` on a valid token

    ```json
    {"username": "your-username"}
    ```

- `401 Unauthorised` if the token is missing or invalid

    ```json
    {"error": "Authentication required."}
    ```
