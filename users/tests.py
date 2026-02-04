from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.registration_url = '/auth/registration/'
        self.login_url = '/auth/login/'
        self.user_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'password1': 'testpassword123',
            'password2': 'testpassword123',  # dj-rest-auth registration often requires confirmation match or just password
        }

    def test_user_registration(self):
        response = self.client.post(self.registration_url, self.user_data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        self.assertTrue(User.objects.filter(email=self.user_data['email']).exists())

    def test_user_login(self):
        # Create user first
        user = User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )
        
        login_data = {
            'username': self.user_data['username'], # or email depending on settings
            'password': self.user_data['password']
        }
        
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if access token is in response or cookie (since we set JWT cookies)
        self.assertIn('eisa-auth', response.cookies)
