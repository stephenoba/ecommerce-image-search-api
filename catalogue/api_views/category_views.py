from rest_framework import generics
from catalogue.models import Category
from catalogue.serializers.category_serializers import CategorySerializer
from rest_framework.permissions import AllowAny

class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
