from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from catalogue.models import Order, OrderItem, Cart
from catalogue.serializers.order_serializers import OrderSerializer, OrderCreateSerializer, OrderItemSerializer
from catalogue.permissions import IsAdminUser

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders.
    - List: Returns orders for the authenticated user.
    - Create: Checkout from active cart.
    - Retrieve: Order details.
    - Update: Admin only to update status.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        # Only admin can use the standard update (PUT/PATCH) for status changes etc.
        if not request.user.is_staff:
            return Response({"error": "Only admins can update order status directly."}, 
                            status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['put'], url_path='cancel')
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == 'cancelled':
            return Response({"message": "Order is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Non-admins can only cancel their own pending orders
        if not request.user.is_staff and order.status != 'pending':
            return Response({"error": "Only pending orders can be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            
        order.status = 'cancelled'
        order.save()
        return Response({"message": "Order cancelled successfully."}, status=status.HTTP_200_OK)

class OrderItemListAPIView(generics.ListAPIView):
    """List items for a specific order."""
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        order_id = self.kwargs.get('id')
        if self.request.user.is_staff:
            return OrderItem.objects.filter(order_id=order_id)
        return OrderItem.objects.filter(order_id=order_id, order__user=self.request.user)
