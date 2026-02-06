from django.core.management.base import BaseCommand
from catalogue.models import Product, ProductEmbedding
from catalogue.tasks import generate_image_embedding, update_faiss_index
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Rebuild the FAISS index by generating embeddings for all products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of all embeddings even if they already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        products = Product.objects.all()
        total = products.count()
        
        self.stdout.write(f'Found {total} products. Starting embedding generation...')
        
        count = 0
        errors = 0
        
        for i, product in enumerate(products):
            if not product.image:
                self.stdout.write(self.style.WARNING(f'Skipping product {product.id}: No image.'))
                continue
                
            # Check if embedding already exists
            if not force and ProductEmbedding.objects.filter(product=product).exists():
                # Add existing embedding to FAISS index if it's missing from the file
                # For simplicity in this script, we'll just regenerate if we're rebuilding the whole index
                # but if we wanted to be efficient we'd read from DB.
                # However, usually rebuild_index implies starting fresh with the .bin file too.
                pass
            
            try:
                # Generate embedding
                image_path = product.image.path
                if not os.path.exists(image_path):
                    self.stdout.write(self.style.ERROR(f'Image path does not exist for product {product.id}: {image_path}'))
                    errors += 1
                    continue
                    
                embedding = generate_image_embedding(image_path)
                
                # Save to database
                ProductEmbedding.objects.update_or_create(
                    product=product,
                    defaults={'embedding_vector': embedding.tolist()}
                )
                
                # Update FAISS index
                update_faiss_index(embedding.tolist(), product.id)
                
                count += 1
                if count % 10 == 0:
                    self.stdout.write(f'Processed {count}/{total} products...')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing product {product.id}: {e}'))
                errors += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully processed {count} products.'))
        if errors > 0:
            self.stdout.write(self.style.WARNING(f'Encountered {errors} errors during processing.'))
