from django.db import models
from django.contrib.postgres.fields import ArrayField


class Category(models.Model):
    """
    Category model

    Attributes:
        name (CharField): The name of the category
        slug (SlugField): The slug of the category
        description (TextField): The description of the category
        parent (ForeignKey): The parent category
        created_at (DateTimeField): The date and time the category was created
        updated_at (DateTimeField): The date and time the category was updated
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Product model

    Attributes:
        name (CharField): The name of the product
        sku (CharField): The SKU of the product
        description (TextField): The description of the product
        price (DecimalField): The price of the product
        stock_quantity (IntegerField): The stock quantity of the product
        is_active (BooleanField): Whether the product is active
        image (ImageField): The image of the product
        category (ForeignKey): The category of the product
        created_at (DateTimeField): The date and time the product was created
        updated_at (DateTimeField): The date and time the product was updated
    """
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='product_images/')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductEmbedding(models.Model):
    """
    Product embedding model

    Attributes:
        product (Product): The product associated with the embedding
        embedding_vector (ArrayField): The embedding vector of the product
        created_at (DateTimeField): The date and time the embedding was created
    """
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    embedding_vector = ArrayField(models.FloatField(), size=2048)
    created_at = models.DateTimeField(auto_now_add=True)
        
    def __str__(self):
        return self.product.name


class Cart(models.Model):
    """
    Cart model

    Attributes:
        user (User): The user associated with the cart
        status (CharField): The status of the cart
        created_at (DateTimeField): The date and time the cart was created
        updated_at (DateTimeField): The date and time the cart was updated
    """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=255, 
        choices=[('active', 'Active'), ('frozen', 'Frozen'), ('abandoned', 'Abandoned')], 
        default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        # User's can't have more than three carts, and not more than one active cart
        if self.user.carts.count() >= 3:
            raise ValueError("User can't have more than three carts")
        if self.user.carts.filter(status='active').count() >= 1:
            raise ValueError("User can't have more than one active cart")
        super().save(*args, **kwargs)


class CartItem(models.Model):
    """
    Cart item model

    Attributes:
        cart (Cart): The cart associated with the item
        product (Product): The product associated with the item
        quantity (IntegerField): The quantity of the product in the cart
        created_at (DateTimeField): The date and time the item was created
        updated_at (DateTimeField): The date and time the item was updated
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"