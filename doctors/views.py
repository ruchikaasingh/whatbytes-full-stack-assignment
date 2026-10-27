from rest_framework import generics
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from .models import Doctor
from .serializers import DoctorSerializer


class IsCreatorOrReadOnly(BasePermission):
    """Any authenticated user can read doctors; only the creator can modify/delete."""

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.created_by_id == request.user.id


class DoctorListCreateView(generics.ListCreateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated, IsCreatorOrReadOnly]
