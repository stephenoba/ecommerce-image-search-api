from django.db import models


class User(models.Model):
    """
    User model

    Attributes:
        name (CharField): The name of the user
        email (EmailField): The email of the user
        password (CharField): The password of the user
        created_at (DateTimeField): The date and time the user was created
        updated_at (DateTimeField): The date and time the user was updated
    """
    name = models.CharField(max_length=255)
    email = models.EmailField()
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
        

class Address(models.Model):
    """
    Address model

    Attributes:
        user (User): The user associated with the address
        street (CharField): The street of the address
        city (CharField): The city of the address
        state (CharField): The state of the address
        zip_code (CharField): The zip code of the address
        created_at (DateTimeField): The date and time the address was created
        updated_at (DateTimeField): The date and time the address was updated
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Address for {self.user.name}'