@after profile.md

Users can create multiple tokens for API authorisation.
Tokens are managed on the profile page.

Use django-rest-framework and django-rest-knox for token authentication.
Knox handles token hashing (shown once at creation, never retrievable).

Optionally, tokens can be named to help users identify them.

- [X] user can create a token
- [X] user can delete any token
