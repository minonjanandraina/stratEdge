from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, UserSearchSerializer, UserCreateSerializer, ChangePasswordSerializer, UserProfileSerializer
from .models import UserProfile


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserCreateSerializer


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        update_session_auth_hash(request, request.user)
        return Response({'detail': 'Mot de passe modifié avec succès.'})


class _UserSearchPagination(PageNumberPagination):
    page_size = 20


class UserListView(generics.ListAPIView):
    queryset = User.objects.only(
        'id', 'username', 'first_name', 'last_name', 'email'
    ).filter(is_active=True)
    serializer_class = UserSearchSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    pagination_class = _UserSearchPagination


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.select_related('profile')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class UpdateProfileView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile
