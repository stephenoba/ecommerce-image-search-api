from django.core.management.base import BaseCommand
from catalogue.models import Category, Product
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw
from io import BytesIO
import random
from faker import Faker

class Command(BaseCommand):
    help = 'Populate the database with dummy data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')
        fake = Faker()
        
        # Clear existing data
        Product.objects.all().delete()
        Category.objects.all().delete()
        
        # Create categories
        categories = ['Electronics', 'Clothing', 'Home & Kitchen', 'Books', 'Toys', 'Sports', 'Beauty', 'Automotive']
        category_objects = []
        for cat_name in categories:
            cat = Category.objects.create(
                name=cat_name,
                slug=cat_name.lower().replace(' & ', '-').replace(' ', '-'),
                description=fake.text()
            )
            category_objects.append(cat)
            self.stdout.write(f'Created category: {cat_name}')
            
        # Create products
        for i in range(200):
            category = random.choice(category_objects)
            name = fake.sentence(nb_words=3).replace('.', '')
            price = random.uniform(10.0, 1000.0)
            stock = random.randint(0, 500)
            
            product = Product(
                name=name,
                sku=fake.ean13(),
                description=fake.paragraph(),
                price=round(price, 2),
                stock_quantity=stock,
                category=category,
                is_active=True
            )
            
            # Generate dummy image
            img_io = BytesIO()
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            img = Image.new('RGB', (600, 600), color=color)
            draw = ImageDraw.Draw(img)
            # Draw random usage of lines/shapes
            for _ in range(5):
                shape_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                x1, x2 = sorted([random.randint(0, 600) for _ in range(2)])
                y1, y2 = sorted([random.randint(0, 600) for _ in range(2)])
                draw.rectangle([x1, y1, x2, y2], outline=shape_color, width=3)
            
            img.save(img_io, format='JPEG')
            
            filename = f'product_{i+1}.jpg'
            product.image.save(filename, ContentFile(img_io.getvalue()), save=False)
            product.save()
            
            if (i + 1) % 10 == 0:
                self.stdout.write(f'Created {i+1} products...')
            
        self.stdout.write(self.style.SUCCESS('Database seeded successfully with 200 products!'))
