from http import HTTPStatus

from django.shortcuts import redirect, render
from django.views import View

from help.models import HelpWiki
from wikis.models import Page


class HelpPageView(View):
    def get(self, request, path=""):
        wiki = HelpWiki.objects.first()

        if path == "index":
            return redirect("/help/")
        elif path.endswith("/index"):
            return redirect(request.path.rsplit("/index", 1)[0] + "/")
        elif path == "" or path.endswith("/"):
            path = f"{path}index"

        if not wiki:
            return render(
                request,
                "help/not_found.html",
                {"path": path},
                status=HTTPStatus.NOT_FOUND,
            )

        try:
            page = wiki.get_page(path=path)
        except Page.DoesNotExist:
            return render(
                request,
                "help/not_found.html",
                {"path": path},
                status=HTTPStatus.NOT_FOUND,
            )

        version = page.latest_version
        content = version.render(base_url="/help/")

        return render(request, "help/page.html", {
            "page": version,
            "content": content,
        })
