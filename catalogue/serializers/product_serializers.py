from rest_framework import serializers
from catalogue.models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'price', 'stock_quantity', 'image', 'category']