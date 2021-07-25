from django.shortcuts import render
from rest_framework import viewsets
from .models import Character
from .serializers import CharacterSerializer


class CharacterViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = Character.objects.all()
    serializer_class = CharacterSerializer
