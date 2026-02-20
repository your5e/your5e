from django.db.models import Q

from users.models import User


class EmailOrUserBackend:
    def authenticate(self, request, username=None, password=None):
        if username is None or password is None:
            return None

        try:
            user = User.objects.get(Q(username=username) | Q(email=username))
        except User.DoesNotExist:
            return None

        if not user.is_active:
            return None

        if user.check_password(password):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
