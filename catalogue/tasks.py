import logging
import time
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from django.conf import settings
from celery import shared_task
from .models import Product, ProductEmbedding
import faiss
import os

logger = logging.getLogger(__name__)

# Constants
INDEX_FILE = getattr(settings, 'FAISS_INDEX_PATH', os.path.join(settings.BASE_DIR, 'faiss_index.bin'))
EMBEDDING_DIM = 2048

def get_model():
    # Load pre-trained ResNet50 model
    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    # Remove the last fully connected layer to get embeddings
    modules = list(model.children())[:-1]
    model = torch.nn.Sequential(*modules)
    model.eval()
    return model

def get_transform():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

def update_faiss_index(embedding, product_id):
    # This is a naive implementation. In production, consider using a dedicated vector DB or handling concurrency limits.
    index = None
    if os.path.exists(INDEX_FILE):
        index = faiss.read_index(INDEX_FILE)
    else:
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        # Using ID map to store product IDs
        index = faiss.IndexIDMap(index)

    # Faiss expects numpy array of float32
    embedding_np = np.array([embedding], dtype='float32')
    ids_np = np.array([product_id], dtype='int64')

    index.add_with_ids(embedding_np, ids_np)
    faiss.write_index(index, INDEX_FILE)

@shared_task
def generate_embedding(product_id):
    try:
        product = Product.objects.get(id=product_id)
        if not product.image:
            logger.warning(f"Product {product_id} has no image.")
            return

        # Prepare model and transform
        model = get_model()
        preprocess = get_transform()

        # Load and preprocess image
        image_path = product.image.path
        image = Image.open(image_path).convert('RGB')
        input_tensor = preprocess(image)
        input_batch = input_tensor.unsqueeze(0)  # Create a mini-batch as expected by the model

        # Generate embedding
        with torch.no_grad():
            output = model(input_batch)
        
        # Flatten the output 
        embedding = output.squeeze().numpy().tolist()

        # Save to database
        ProductEmbedding.objects.update_or_create(
            product=product,
            defaults={'embedding_vector': embedding}
        )

        # Update FAISS index
        update_faiss_index(embedding, product.id)
        
        logger.info(f"Successfully generated embedding for product {product_id}")

    except Product.DoesNotExist:
        logger.error(f"Product {product_id} not found.")
    except Exception as e:
        logger.error(f"Error generating embedding for product {product_id}: {e}")
