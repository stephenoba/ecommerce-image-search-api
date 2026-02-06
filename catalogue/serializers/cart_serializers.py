from rest_framework import serializers
from catalogue.models import Cart, CartItem
from catalogue.serializers.product_serializers import ProductSerializer

class CartItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product', 'product_details', 'quantity', 'created_at', 'updated_at']
        read_only_fields = ['cart']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source='cartitem_set', many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'status', 'items', 'total_price', 'created_at', 'updated_at']
    
    def get_total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.cartitem_set.all())
