from django.urls import path
from catalogue.api_views.category_views import CategoryListAPIView

urlpatterns = [
    path('categories/', CategoryListAPIView.as_view(), name='category-list'),
]
