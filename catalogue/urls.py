from django.urls import path, include
from rest_framework.routers import DefaultRouter
from catalogue.api_views.category_views import CategoryListAPIView
from catalogue.api_views.product_views import (
    ProductListAPIView, ProductByCategoryListAPIView, 
    ProductCreateAPIView, ProductImageSearchAPIView,
    ProductDetailAPIView
)
from catalogue.api_views.cart_views import CartActiveAPIView, CartItemViewSet, CartClearAPIView

router = DefaultRouter()
router.register(r'cart/items', CartItemViewSet, basename='cart-item')

urlpatterns = [
    path('', include(router.urls)),
    path('categories/', CategoryListAPIView.as_view(), name='category-list'),
    path('products/', ProductListAPIView.as_view(), name='product-list'),
    path('products/create/', ProductCreateAPIView.as_view(), name='product-create'),
    path('products/<int:id>/', ProductDetailAPIView.as_view(), name='product-detail'),
    path('products/search/upload/', ProductImageSearchAPIView.as_view(), name='product-search-upload'),
    path('products/category/<slug:slug>/', ProductByCategoryListAPIView.as_view(), name='product-by-category'),
    path('cart/active/', CartActiveAPIView.as_view(), name='cart-active'),
    path('cart/clear/', CartClearAPIView.as_view(), name='cart-clear'),
]
