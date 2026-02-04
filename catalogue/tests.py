from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from catalogue.models import Category

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
        # Assuming defaults page size didn't paginate it into 'results'. 
        # But generics.ListAPIView usually uses pagination if configured. 
        # I should check if pagination is default.
        # If paginated, response.data would be a dict with 'results' key.
        # Or I can check response.data['results'] if it fails.
        # Let's simple check if 'results' in response.data
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 2)
            self.assertEqual(response.data['results'][0]['name'], 'Electronics')
            self.assertEqual(response.data['results'][1]['name'], 'Clothing')
        else:
            self.assertEqual(len(response.data), 2)
            self.assertEqual(response.data[0]['name'], 'Electronics')
            self.assertEqual(response.data[1]['name'], 'Clothing')
