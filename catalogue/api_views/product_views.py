from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from catalogue.models import Product
from catalogue.serializers.product_serializers import ProductSerializer, ProductCreateSerializer
from catalogue.serializers.search_serializers import ImageSearchSerializer, ProductSearchResultSerializer
from catalogue.tasks import generate_embedding, generate_image_embedding, search_similar_products
from catalogue.permissions import IsAdminUser
import tempfile
import os

class ProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    pagination_class = ProductPagination

    def get_queryset(self):
        queryset = Product.objects.all()

        #Filtering by category_slug
        category_slug = self.request.query_params.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filtering by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
            
        # Filtering by stock quantity
        min_stock = self.request.query_params.get('min_stock')
        max_stock = self.request.query_params.get('max_stock')
        
        if min_stock:
            queryset = queryset.filter(stock_quantity__gte=min_stock)
        if max_stock:
            queryset = queryset.filter(stock_quantity__lte=max_stock)
            
        return queryset

class ProductByCategoryListAPIView(ProductListAPIView):
    # This is actually unneccessary since we are already filtering by category_slug in the ProductListAPIView
    # But I will keep it for now
    def get_queryset(self):
        queryset = super().get_queryset()
        slug = self.kwargs['slug']
        return queryset.filter(category__slug=slug)


class ProductCreateAPIView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        product = serializer.save()
        # Trigger async task to generate embedding
        generate_embedding.delay(product.id)


class ProductImageSearchAPIView(APIView):
    """
    API View for searching products by image similarity.
    Accepts an uploaded image and returns similar products.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(request_body=ImageSearchSerializer)
    def post(self, request, *args, **kwargs):
        serializer = ImageSearchSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_image = serializer.validated_data['image']
        limit = serializer.validated_data.get('limit', 10)
        
        # Save uploaded image to temporary file
        temp_file = None
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            for chunk in uploaded_image.chunks():
                temp_file.write(chunk)
            temp_file.close()
            
            # Generate embedding for the uploaded image
            query_embedding = generate_image_embedding(temp_file.name)
            
            # Search for similar products
            search_results = search_similar_products(query_embedding, k=limit)
            
            if not search_results:
                return Response({
                    'results': [],
                    'message': 'No similar products found.'
                }, status=status.HTTP_200_OK)
            
            # Fetch products and attach similarity scores
            product_ids = [pid for pid, _ in search_results]
            products = Product.objects.filter(id__in=product_ids)
            
            # Create a mapping of product_id to distance
            distance_map = {pid: distance for pid, distance in search_results}
            
            # Attach similarity scores and sort by distance
            results = []
            for product in products:
                distance = distance_map.get(product.id, float('inf'))
                product.similarity_score = 1.0 / (1.0 + distance)
                results.append(product)
            
            # Sort by similarity score descending
            results.sort(key=lambda x: x.similarity_score, reverse=True)

            result_serializer = ProductSearchResultSerializer(results, many=True)
            
            return Response({
                'results': result_serializer.data,
                'count': len(results)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error processing image search: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)