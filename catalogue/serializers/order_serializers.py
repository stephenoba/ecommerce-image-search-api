from decimal import Decimal
from rest_framework import serializers
from catalogue.models import Order, OrderItem, Cart, CartItem
from catalogue.serializers.product_serializers import ProductSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'product_details', 'quantity', 'unit_price', 'line_total', 'created_at']
        read_only_fields = ['order', 'unit_price', 'line_total']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'user', 'status', 'sub_total', 'tax', 'total', 'items', 'created_at', 'updated_at']
        read_only_fields = ['user', 'sub_total', 'tax', 'total']

class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'status', 'sub_total', 'tax', 'total']
        read_only_fields = ['id', 'status', 'sub_total', 'tax', 'total']

    def create(self, validated_data):
        user = self.context['request'].user
        cart = Cart.objects.filter(user=user, status='active').first()
        
        if not cart or not cart.cartitem_set.exists():
            raise serializers.ValidationError("Active cart is empty or does not exist.")
            
        # Calculate totals
        sub_total = sum(item.product.price * item.quantity for item in cart.cartitem_set.all())
        tax = sub_total * Decimal('0.1')
        total = sub_total + tax
        
        # Create Order
        order = Order.objects.create(
            user=user,
            status='pending',
            sub_total=sub_total,
            tax=tax,
            total=total
        )
        
        # Create OrderItems and transfer from CartItems
        for cart_item in cart.cartitem_set.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.price,
                line_total=cart_item.product.price * cart_item.quantity
            )
            
        # Freeze the cart
        cart.status = 'frozen'
        cart.save()
        
        return order
