from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from catalogue.models import Cart, CartItem, Product
from catalogue.serializers.cart_serializers import CartSerializer, CartItemSerializer

class CartActiveAPIView(generics.RetrieveAPIView):
    """Get the active user's cart."""
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user, status='active')
        return cart

class CartItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cart items.
    Allows listing, adding, updating, and removing items.
    """
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return items from the user's active cart
        return CartItem.objects.filter(cart__user=self.request.user, cart__status='active')

    def perform_create(self, serializer):
        cart, created = Cart.objects.get_or_create(user=self.request.user, status='active')
        product = serializer.validated_data['product']
        quantity = serializer.validated_data.get('quantity', 1)
        
        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
            # We don't call serializer.save() here because we handled it
        else:
            serializer.save(cart=cart)

class CartClearAPIView(APIView):
    """Clear the entire active cart."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        cart = Cart.objects.filter(user=request.user, status='active').first()
        if cart:
            cart.cartitem_set.all().delete()
            return Response({"message": "Cart cleared successfully."}, status=status.HTTP_204_NO_CONTENT)
        return Response({"message": "No active cart found."}, status=status.HTTP_404_NOT_FOUND)
