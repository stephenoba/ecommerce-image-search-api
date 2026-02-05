from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import sys
from unittest.mock import MagicMock

from catalogue.models import Category
from catalogue.models import Product

# Mock psycopg2 and ArrayField to avoid import errors with SQLite/Broken Env
sys.modules['psycopg2'] = MagicMock()
sys.modules['django.contrib.postgres'] = MagicMock()
sys.modules['django.contrib.postgres.fields'] = MagicMock()

# We need to ensure ArrayField is available as a class
class MockArrayField:
    def __init__(self, *args, **kwargs):
        pass

sys.modules['django.contrib.postgres.fields'].ArrayField = MockArrayField



class CategoryAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category1 = Category.objects.create(name='Electronics', slug='electronics', description='Electronic items')
        self.category2 = Category.objects.create(name='Clothing', slug='clothing', description='Clothing items')

    def test_get_category_list(self):
        url = reverse('category-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 2)
            self.assertEqual(response.data['results'][0]['name'], 'Electronics')
            self.assertEqual(response.data['results'][1]['name'], 'Clothing')
        else:
            self.assertEqual(len(response.data), 2)
            self.assertEqual(response.data[0]['name'], 'Electronics')
            self.assertEqual(response.data[1]['name'], 'Clothing')


class ProductAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        
        # Create 15 products for pagination test
        for i in range(15):
            Product.objects.create(
                name=f'Product {i}',
                sku=f'SKU-{i}',
                description=f'Description {i}',
                price=10.0 + i,
                stock_quantity=5 + i,
                category=self.category,
                image='path/to/image.jpg'
            )
            
    def test_list_products_pagination(self):
        url = reverse('product-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check pagination keys
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        # Default page size is 10
        self.assertEqual(len(response.data['results']), 10)
        self.assertEqual(response.data['count'], 15)
        
    def test_filter_by_price(self):
        url = reverse('product-list')
        # Filter price >= 20.0 (Product 10 to 14) -> 5 products
        response = self.client.get(url, {'min_price': 20.0})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 15 products. Prices: 10, 11, ..., 24.
        # >= 20: 20, 21, 22, 23, 24 -> 5 products.
        self.assertEqual(response.data['count'], 5)
        
        # Filter price <= 14.0 (Product 0 to 4) -> 5 products
        response = self.client.get(url, {'max_price': 14.0})
        self.assertEqual(response.data['count'], 5)

    def test_filter_by_stock(self):
        url = reverse('product-list')
         # Stock: 5, 6, ..., 19.
        # Filter stock >= 15 (Product 10 to 14) -> 5 products
        response = self.client.get(url, {'min_stock': 15})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 5)

    def test_get_products_by_category(self):
        # Create another category and product
        other_category = Category.objects.create(name='Clothing', slug='clothing')
        Product.objects.create(
            name='T-Shirt',
            sku='SKU-CLOTHING-1',
            description='A nice t-shirt',
            price=20.0,
            stock_quantity=10,
            category=other_category,
            image='path/to/image.jpg'
        )

        url = reverse('product-by-category', kwargs={'slug': 'electronics'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return only electronics products (15 created in setUp)
        self.assertEqual(response.data['count'], 15)
        
        # Test clothing category
        url = reverse('product-by-category', kwargs={'slug': 'clothing'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'T-Shirt')


from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import User
from PIL import Image
import io


class ProductCreateAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Electronics', slug='electronics', description='Electronic items')
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
            is_staff=False
        )
        
        # Create a simple test image
        self.test_image = self.create_test_image()
        
    def create_test_image(self):
        """Create a simple test image"""
        image = Image.new('RGB', (100, 100), color='red')
        image_file = io.BytesIO()
        image.save(image_file, 'JPEG')
        image_file.seek(0)
        return SimpleUploadedFile(
            name='test_image.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )
    
    @patch('catalogue.api_views.product_views.generate_embedding.delay')
    def test_create_product_as_admin(self, mock_task):
        """Test that admin users can create products"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('product-create')
        data = {
            'name': 'Test Product',
            'sku': 'TEST-SKU-001',
            'description': 'Test description',
            'price': '29.99',
            'stock_quantity': 100,
            'category': self.category.id,
            'image': self.create_test_image()
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Product')
        self.assertEqual(response.data['sku'], 'TEST-SKU-001')
        
        # Verify the task was called
        mock_task.assert_called_once()
        
        # Verify product was created
        product = Product.objects.get(sku='TEST-SKU-001')
        self.assertEqual(product.name, 'Test Product')
    
    def test_create_product_as_regular_user(self):
        """Test that regular users cannot create products"""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('product-create')
        data = {
            'name': 'Test Product',
            'sku': 'TEST-SKU-002',
            'description': 'Test description',
            'price': '29.99',
            'stock_quantity': 100,
            'category': self.category.id,
            'image': self.create_test_image()
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify product was NOT created
        self.assertFalse(Product.objects.filter(sku='TEST-SKU-002').exists())
    
    def test_create_product_unauthenticated(self):
        """Test that unauthenticated users cannot create products"""
        url = reverse('product-create')
        data = {
            'name': 'Test Product',
            'sku': 'TEST-SKU-003',
            'description': 'Test description',
            'price': '29.99',
            'stock_quantity': 100,
            'category': self.category.id,
            'image': self.create_test_image()
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Verify product was NOT created
        self.assertFalse(Product.objects.filter(sku='TEST-SKU-003').exists())
    
    @patch('catalogue.api_views.product_views.generate_embedding.delay')
    def test_create_product_without_image(self, mock_task):
        """Test creating product without image"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('product-create')
        data = {
            'name': 'Test Product No Image',
            'sku': 'TEST-SKU-004',
            'description': 'Test description',
            'price': '29.99',
            'stock_quantity': 100,
            'category': self.category.id
        }
        
        response = self.client.post(url, data, format='multipart')
        
        # This should fail because image is required
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('catalogue.api_views.product_views.generate_embedding.delay')
    def test_create_product_with_invalid_data(self, mock_task):
        """Test creating product with invalid data"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('product-create')
        data = {
            'name': '',  # Invalid: empty name
            'sku': 'TEST-SKU-005',
            'description': 'Test description',
            'price': 'invalid',  # Invalid price
            'stock_quantity': -10,  # Invalid negative stock
            'category': self.category.id,
            'image': self.create_test_image()
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify task was NOT called
        mock_task.assert_not_called()


import os
import tempfile
from catalogue.models import ProductEmbedding
from catalogue.tasks import generate_embedding
from django.core.files.base import ContentFile


class ProductEmbeddingTaskTest(TestCase):
    """Tests for the embedding generation task itself"""
    
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(
            name='Electronics', 
            slug='electronics', 
            description='Electronic items'
        )
        
    def create_test_image(self):
        """Create a simple test image as ContentFile"""
        image = Image.new('RGB', (224, 224), color='blue')
        image_file = io.BytesIO()
        image.save(image_file, 'JPEG')
        image_file.seek(0)
        return ContentFile(image_file.read(), name='test_embed.jpg')
    
    @patch('catalogue.tasks.faiss')
    def test_generate_embedding_creates_product_embedding(self, mock_faiss):
        """Test that generate_embedding task creates ProductEmbedding"""
        # Create product with image
        product = Product.objects.create(
            name='Test Product',
            sku='TEST-EMBED-001',
            description='Test description',
            price=29.99,
            stock_quantity=100,
            category=self.category
        )
        product.image.save('test.jpg', self.create_test_image(), save=True)
        
        # Mock FAISS index operations
        mock_index = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_index
        mock_faiss.IndexIDMap.return_value = mock_index
        
        # Run the task
        generate_embedding(product.id)
        
        # Verify ProductEmbedding was created
        self.assertTrue(ProductEmbedding.objects.filter(product=product).exists())
        
        embedding = ProductEmbedding.objects.get(product=product)
        
        # Verify embedding vector has correct length (ResNet50 outputs 2048-dim)
        self.assertEqual(len(embedding.embedding_vector), 2048)
        
        # Verify all values are floats
        self.assertTrue(all(isinstance(x, float) for x in embedding.embedding_vector))
    
    @patch('catalogue.tasks.faiss')
    def test_generate_embedding_updates_faiss_index(self, mock_faiss):
        """Test that FAISS index is updated with new embedding"""
        product = Product.objects.create(
            name='Test Product 2',
            sku='TEST-EMBED-002',
            description='Test description',
            price=29.99,
            stock_quantity=100,
            category=self.category
        )
        product.image.save('test2.jpg', self.create_test_image(), save=True)
        
        # Mock FAISS index operations
        mock_index = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_index
        mock_faiss.IndexIDMap.return_value = mock_index
        mock_faiss.read_index.return_value = mock_index
        
        # Run the task
        generate_embedding(product.id)
        
        # Verify FAISS operations were called
        # add_with_ids should be called with embedding and product ID
        mock_index.add_with_ids.assert_called_once()
        
        # Verify write_index was called to persist the index
        mock_faiss.write_index.assert_called_once()
    
    @patch('catalogue.tasks.faiss')
    def test_generate_embedding_with_existing_embedding(self, mock_faiss):
        """Test that existing embeddings are updated, not duplicated"""
        product = Product.objects.create(
            name='Test Product 3',
            sku='TEST-EMBED-003',
            description='Test description',
            price=29.99,
            stock_quantity=100,
            category=self.category
        )
        product.image.save('test3.jpg', self.create_test_image(), save=True)
        
        # Create initial embedding
        ProductEmbedding.objects.create(
            product=product,
            embedding_vector=[0.0] * 2048
        )
        
        # Mock FAISS
        mock_index = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_index
        mock_faiss.IndexIDMap.return_value = mock_index
        
        # Run the task again
        generate_embedding(product.id)
        
        # Verify only one ProductEmbedding exists
        self.assertEqual(ProductEmbedding.objects.filter(product=product).count(), 1)
        
        # Verify embedding was updated (not all zeros anymore)
        embedding = ProductEmbedding.objects.get(product=product)
        self.assertNotEqual(embedding.embedding_vector, [0.0] * 2048)
    
    @patch('catalogue.tasks.logger')
    def test_generate_embedding_handles_missing_image(self, mock_logger):
        """Test that task handles products without images gracefully"""
        product = Product.objects.create(
            name='Test Product No Image',
            sku='TEST-EMBED-004',
            description='Test description',
            price=29.99,
            stock_quantity=100,
            category=self.category
            # No image
        )
        
        # Run the task
        generate_embedding(product.id)
        
        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        
        # Verify no embedding was created
        self.assertFalse(ProductEmbedding.objects.filter(product=product).exists())
    
    @patch('catalogue.tasks.logger')
    def test_generate_embedding_handles_nonexistent_product(self, mock_logger):
        """Test that task handles non-existent products gracefully"""
        fake_product_id = 99999
        
        # Run the task with non-existent ID
        generate_embedding(fake_product_id)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
