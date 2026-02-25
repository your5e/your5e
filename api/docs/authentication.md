# Authentication

All API requests must include an authentication token.

```
curl -H "Authorization: Token [token]" https://your5e.com/api/ping
```

Token are generated and revoked via your profile. You can name them to help
you remember their purpose.

Tokens do not expire, but can be revoked when no longer needed or compromised.
