from rest_framework import viewsets
from rest_framework.permissions import AllowAny, DjangoModelPermissions, IsAuthenticated
from nucleus.permissions import AdminOrReadOnly
from .models import Character
from .serializers import CharacterSerializer


class CharacterViewSet(viewsets.ModelViewSet):
    queryset = Character.objects.all()
    serializer_class = CharacterSerializer
    permission_classes = [IsAuthenticated]
    # permission_classes = [AdminOrReadOnly]


class FullDjangoModelPermissions(DjangoModelPermissions):
    def __init__(self):
        self.perms_map["GET"] = ["%(app_label)s.view_%(model_name)s"]
        self.perms_map["OPTIONS"] = ["%(app_label)s.view_%(model_name)s"]
        self.perms_map["HEAD"] = ["%(app_label)s.view_%(model_name)s"]
        self.perms_map["POST"] = ["%(app_label)s.add_%(model_name)s"]
        self.perms_map["PUT"] = ["%(app_label)s.change_%(model_name)s"]
