from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import sys
from unittest.mock import MagicMock
import numpy as np

from catalogue.models import Category
from catalogue.models import Product, ProductEmbedding, Cart, CartItem, Order, OrderItem
from users.models import User

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
        
        # Verify embedding vector has correct length (2048)
        self.assertEqual(len(embedding.embedding_vector), 2048)
        
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


class ProductImageSearchAPITest(TestCase):
    """Tests for the image search API endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            description='Electronic items'
        )
        
    def create_test_image(self):
        """Create a simple test image as UploadedFile"""
        image = Image.new('RGB', (224, 224), color='red')
        image_file = io.BytesIO()
        image.save(image_file, 'JPEG')
        image_file.seek(0)
        return SimpleUploadedFile(
            name='search_test.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )
    
    @patch('catalogue.api_views.product_views.search_similar_products')
    @patch('catalogue.api_views.product_views.generate_image_embedding')
    def test_image_search_with_results(self, mock_generate_embedding, mock_search):
        """Test successful image search with results"""
        # Create test products
        product1 = Product.objects.create(
            name='Product 1',
            sku='SKU-001',
            description='Test product 1',
            price=29.99,
            stock_quantity=100,
            category=self.category
        )
        product2 = Product.objects.create(
            name='Product 2',
            sku='SKU-002',
            description='Test product 2',
            price=39.99,
            stock_quantity=50,
            category=self.category
        )
        
        # Mock embedding generation and search
        mock_generate_embedding.return_value = np.zeros(2048)
        mock_search.return_value = [
            (product1.id, 0.5),  # Lower distance = more similar
            (product2.id, 1.2)
        ]
        
        url = reverse('product-search-upload')
        data = {'image': self.create_test_image()}
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 2)
        
        # Verify results are ordered by similarity score (descending)
        results = response.data['results']
        self.assertEqual(len(results), 2)
        
        # First result should be product1 (lower distance = higher similarity)
        self.assertEqual(results[0]['id'], product1.id)
        self.assertIn('similarity_score', results[0])
        
        # Similarity scores should be in descending order
        self.assertGreater(results[0]['similarity_score'], results[1]['similarity_score'])
    
    @patch('catalogue.api_views.product_views.search_similar_products')
    @patch('catalogue.api_views.product_views.generate_image_embedding')
    def test_image_search_no_results(self, mock_generate_embedding, mock_search):
        """Test image search when no similar products found"""
        mock_generate_embedding.return_value = np.zeros(2048)
        mock_search.return_value = []
        
        url = reverse('product-search-upload')
        data = {'image': self.create_test_image()}
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [])
        self.assertIn('message', response.data)
    
    def test_image_search_missing_image(self):
        """Test image search without uploading an image"""
        url = reverse('product-search-upload')
        data = {}
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)
    
    def test_image_search_invalid_image(self):
        """Test image search with invalid image file"""
        url = reverse('product-search-upload')
        
        # Create invalid file (text instead of image)
        invalid_file = SimpleUploadedFile(
            name='test.txt',
            content=b'This is not an image',
            content_type='text/plain'
        )
        
        data = {'image': invalid_file}
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('catalogue.api_views.product_views.search_similar_products')
    @patch('catalogue.api_views.product_views.generate_image_embedding')
    def test_image_search_with_limit_parameter(self, mock_generate_embedding, mock_search):
        """Test image search with custom limit parameter"""
        # Create 5 products
        products = []
        for i in range(5):
            product = Product.objects.create(
                name=f'Product {i}',
                sku=f'SKU-{i}',
                description=f'Test product {i}',
                price=29.99 + i,
                stock_quantity=100,
                category=self.category
            )
            products.append(product)
        
        mock_generate_embedding.return_value = np.zeros(2048)
        # Return all 5 products with different distances
        mock_search.return_value = [(p.id, float(i)) for i, p in enumerate(products)]
        
        url = reverse('product-search-upload')
        data = {
            'image': self.create_test_image(),
            'limit': 3  # Request only top 3
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify search was called with limit=3
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        self.assertEqual(call_args[1]['k'], 3)


class ProductDetailAPITest(TestCase):
    """Tests for the product detail API endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Electronics', slug='electronics', description='Desc')
        self.product = Product.objects.create(
            name='Test Product', sku='SKU-001', description='Desc', 
            price=10.00, stock_quantity=10, category=self.category
        )
        self.admin_user = User.objects.create_superuser(username='admin', password='password', email='admin@test.com')
        self.regular_user = User.objects.create_user(username='user', password='password', email='user@test.com')
        self.url = reverse('product-detail', kwargs={'id': self.product.id})

    def test_get_product_detail_allow_any(self):
        """Anyone can view product details"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.product.name)

    def test_update_product_as_admin(self):
        """Admin can update product"""
        self.client.force_authenticate(user=self.admin_user)
        data = {'name': 'Updated Name'}
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Name')

    def test_update_product_as_regular_user(self):
        """Regular user cannot update product"""
        self.client.force_authenticate(user=self.regular_user)
        data = {'name': 'Updated Name'}
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_product_as_admin(self):
        """Admin can delete product"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())


class CartAPITest(TestCase):
    """Tests for the cart and cart item API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', password='password123', email='user1@test.com')
        self.user2 = User.objects.create_user(username='user2', password='password123', email='user2@test.com')
        self.category = Category.objects.create(name='Electronics', slug='electronics', description='Desc')
        self.product = Product.objects.create(
            name='Laptop', sku='LP-01', description='Desc', 
            price=1000.00, stock_quantity=5, category=self.category
        )
        self.item_url = reverse('cart-item-list')
        self.active_url = reverse('cart-active')
        self.clear_url = reverse('cart-clear')

    def test_add_item_to_cart(self):
        self.client.force_authenticate(user=self.user)
        data = {'product': self.product.id, 'quantity': 2}
        response = self.client.post(self.item_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.first().quantity, 2)

    def test_add_same_item_updates_quantity(self):
        self.client.force_authenticate(user=self.user)
        CartItem.objects.create(
            cart=Cart.objects.create(user=self.user, status='active'),
            product=self.product,
            quantity=1
        )
        data = {'product': self.product.id, 'quantity': 2}
        response = self.client.post(self.item_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CartItem.objects.get().quantity, 3)

    def test_get_active_cart(self):
        self.client.force_authenticate(user=self.user)
        data = {'product': self.product.id, 'quantity': 1}
        self.client.post(self.item_url, data)
        
        response = self.client.get(self.active_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(float(response.data['total_price']), 1000.00)

    def test_cart_isolation(self):
        """User A cannot see User B's cart"""
        # User 1 has item
        cart1 = Cart.objects.create(user=self.user, status='active')
        CartItem.objects.create(cart=cart1, product=self.product, quantity=1)
        
        # User 2 logs in
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(self.active_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Cart for User 2 should be empty (or just created)
        self.assertEqual(len(response.data['items']), 0)

    def test_update_cart_item(self):
        self.client.force_authenticate(user=self.user)
        item = CartItem.objects.create(
            cart=Cart.objects.create(user=self.user, status='active'),
            product=self.product,
            quantity=1
        )
        url = reverse('cart-item-detail', kwargs={'pk': item.id})
        response = self.client.patch(url, {'quantity': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

    def test_delete_cart_item(self):
        self.client.force_authenticate(user=self.user)
        item = CartItem.objects.create(
            cart=Cart.objects.create(user=self.user, status='active'),
            product=self.product,
            quantity=1
        )
        url = reverse('cart-item-detail', kwargs={'pk': item.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_clear_cart(self):
        self.client.force_authenticate(user=self.user)
        cart = Cart.objects.create(user=self.user, status='active')
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        
        response = self.client.delete(self.clear_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)


class OrderAPITest(TestCase):
    """Tests for the order and checkout API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', password='password123', email='user1@test.com')
        self.admin = User.objects.create_superuser(username='admin', password='password123', email='admin@test.com')
        self.category = Category.objects.create(name='Electronics', slug='electronics', description='Desc')
        self.product = Product.objects.create(
            name='Laptop', sku='LP-01', description='Desc', 
            price=1000.00, stock_quantity=5, category=self.category
        )
        self.cart = Cart.objects.create(user=self.user, status='active')
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)
        
        self.order_url = reverse('order-list')
        self.admin_url = reverse('order-list')

    def test_checkout_creates_order(self):
        """POST /orders/ should create an order from active cart"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.order_url, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        
        # Verify cart is frozen
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, 'frozen')
        
        # Verify order items
        order = Order.objects.first()
        self.assertEqual(order.orderitem_set.count(), 1)
        self.assertEqual(order.orderitem_set.first().product, self.product)
        self.assertEqual(float(order.total), 1100.00) # 1000 + 10% tax

    def test_list_user_orders(self):
        self.client.force_authenticate(user=self.user)
        # Create an order
        self.client.post(self.order_url, {})
        
        response = self.client.get(self.order_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_order_details(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.order_url, {})
        order_id = resp.data['id']
        
        url = reverse('order-detail', kwargs={'pk': order_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], order_id)
        self.assertEqual(len(response.data['items']), 1)

    def test_admin_update_order_status(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.order_url, {})
        order_id = resp.data['id']
        
        url = reverse('order-detail', kwargs={'pk': order_id})
        
        # Regular user fails
        data = {'status': 'completed'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin user succeeds
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, 'completed')

    def test_cancel_order(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.order_url, {})
        order_id = resp.data['id']
        
        url = reverse('order-cancel', kwargs={'pk': order_id})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, 'cancelled')

    def test_get_order_items(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.order_url, {})
        order_id = resp.data['id']
        
        url = reverse('order-items', kwargs={'id': order_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['product'], self.product.id)
