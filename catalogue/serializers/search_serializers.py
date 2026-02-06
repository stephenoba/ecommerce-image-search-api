from rest_framework import serializers
from catalogue.models import Product


class ImageSearchSerializer(serializers.Serializer):
    """Serializer for image search input"""
    image = serializers.ImageField(required=True)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100, required=False)


class ProductSearchResultSerializer(serializers.ModelSerializer):
    """Serializer for product search results with similarity score"""
    similarity_score = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'description', 'price', 'stock_quantity', 
                  'image', 'category', 'similarity_score']
