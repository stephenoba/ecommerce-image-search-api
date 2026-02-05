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
