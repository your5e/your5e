@after ../build/setup.md

Using a custom user model deliberately, because names aren't first/last
(django should really know better by now).

- username, required, unique
- email, required, unique, validated
- password, required
- name, one field (eg. "Mark Norman Francis"), not required, not unique
- short_name, (eg. "Norm"), not required, not unique

Referring to a user by name uses short, name, username in that order,
until not `None`.

- [ ] Create user model
- [ ] Provide sentinel user
- [ ] Provide default `admin` superuser and `norm` account in development

Authenticating to the site.

- [ ] Login accepts either username or email as identifier
