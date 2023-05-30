"""website URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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

# from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import GraphQLView

# from strawberry.django.views import AsyncGraphQLView
from .types import schema

# from graphene_django.views import GraphQLView
# from rest_framework import routers

# from character.views import CharacterViewSet
# from item.views import ItemViewSet, ArmorViewSet, EquipmentViewSet, WeaponViewSet
# from place.views import (
#     PlanetViewSet,
#     RegionViewSet,
#     TownViewSet,
#     DistrictViewSet,
#     LocationViewSet,
# )

# from .views import introspection_schema

admin.site.site_header = "D&D Admin"
admin.site.index_title = "Admin"


# Routers provide an easy way of automatically determining the URL conf.
# router = routers.DefaultRouter()
# router.register(r"characters", CharacterViewSet)
# router.register(r"items", ItemViewSet)
# router.register(r"equipment", EquipmentViewSet)
# router.register(r"armor", ArmorViewSet)
# router.register(r"weapons", WeaponViewSet)
# router.register(r"planets", PlanetViewSet)
# router.register(r"regions", RegionViewSet)
# router.register(r"towns", TownViewSet)
# router.register(r"districts", DistrictViewSet)
# router.register(r"locations", LocationViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("admin/", admin.site.urls),
    # path("", include(router.urls)),
    path("__debug__/", include("debug_toolbar.urls")),
    # path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # path("auth/", include("djoser.urls")),
    # path("auth/", include("djoser.urls.authtoken")),
    # path("graphql/schema/", csrf_exempt(introspection_schema)),
    # path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=False))),
    # path("graphiql/", csrf_exempt(GraphQLView.as_view(graphiql=settings.DEBUG))),
    path("graphql/", GraphQLView.as_view(schema=schema)),
    # path("graphql/", AsyncGraphQLView.as_view(schema=schema)),
]
