"""website URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import GraphQLView
from django.http import HttpResponse
from website import settings


# from strawberry.django.views import AsyncGraphQLView
from .types import schema

admin.site.site_header = "D&D Admin"
admin.site.index_title = "Admin"


def healthcheck(request):
    return HttpResponse("OK")


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("healthcheck/", healthcheck),
    path("admin/", admin.site.urls),
    path("__debug__/", include("debug_toolbar.urls")),
    path(
        "graphiql/",
        csrf_exempt(GraphQLView.as_view(schema=schema, graphiql=settings.DEBUG)),
    ),
    path("graphql/", csrf_exempt(GraphQLView.as_view(schema=schema))),
    # path("graphql/", AsyncGraphQLView.as_view(schema=schema)),
]
