from django.conf import settings


def git_sha(request):
    return {"git_sha": settings.GIT_SHA}
