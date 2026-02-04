from django.urls import path
from catalogue.api_views.category_views import CategoryListAPIView

from catalogue.api_views.product_views import ProductListAPIView

urlpatterns = [
    path('categories/', CategoryListAPIView.as_view(), name='category-list'),
    path('products/', ProductListAPIView.as_view(), name='product-list'),
]
