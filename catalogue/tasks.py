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

# Global cache to prevent redundant loading
_MODEL = None
_FAISS_INDEX = None

def get_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
        
    # Load pre-trained ResNet50 model
    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    # Remove the last fully connected layer to get embeddings
    modules = list(model.children())[:-1]
    _MODEL = torch.nn.Sequential(*modules)
    _MODEL.eval()
    return _MODEL

def get_transform():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

def update_faiss_index(embedding, product_id):
    # This is a naive implementation. In production, consider using a dedicated vector DB or handling concurrency limits.
    global _FAISS_INDEX
    
    if _FAISS_INDEX is None:
        if os.path.exists(INDEX_FILE):
            _FAISS_INDEX = faiss.read_index(INDEX_FILE)
        else:
            base_index = faiss.IndexFlatL2(EMBEDDING_DIM)
            # Using ID map to store product IDs
            _FAISS_INDEX = faiss.IndexIDMap(base_index)

    # Faiss expects numpy array of float32
    embedding_np = np.array([embedding], dtype='float32')
    ids_np = np.array([product_id], dtype='int64')

    _FAISS_INDEX.add_with_ids(embedding_np, ids_np)
    faiss.write_index(_FAISS_INDEX, INDEX_FILE)

def generate_image_embedding(image_path):
    """
    Generate embedding for an image file.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        numpy array: 2048-dimensional embedding vector
    """
    model = get_model()
    preprocess = get_transform()
    
    # Load and preprocess image
    image = Image.open(image_path).convert('RGB')
    input_tensor = preprocess(image)
    input_batch = input_tensor.unsqueeze(0)
    
    # Generate embedding
    with torch.no_grad():
        output = model(input_batch)
    
    # Flatten and return as numpy array
    embedding = output.squeeze().numpy()
    return embedding

def search_similar_products(query_embedding, k=10):
    """
    Search for similar products using FAISS.
    
    Args:
        query_embedding: numpy array of the query image embedding
        k: number of similar products to return
        
    Returns:
        list of tuples: [(product_id, distance), ...]
    """
    global _FAISS_INDEX
    
    if not os.path.exists(INDEX_FILE) and _FAISS_INDEX is None:
        logger.warning("FAISS index file not found and index not in memory. No products to search.")
        return []
    
    try:
        if _FAISS_INDEX is None:
            _FAISS_INDEX = faiss.read_index(INDEX_FILE)
        
        # Ensure query is 2D array of float32
        query_np = np.array([query_embedding], dtype='float32')
        
        # Search for k nearest neighbors
        # distances are L2 distances (lower is more similar)
        distances, indices = _FAISS_INDEX.search(query_np, k)
        
        # indices[0] contains the product IDs, distances[0] contains the distances
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx != -1:  # -1 indicates no result found
                results.append((int(idx), float(distance)))
        
        return results
    except Exception as e:
        logger.error(f"Error searching FAISS index: {e}")
        return []

@shared_task
def generate_embedding(product_id):
    try:
        product = Product.objects.get(id=product_id)
        if not product.image:
            logger.warning(f"Product {product_id} has no image.")
            return

        # Generate embedding using helper function
        image_path = product.image.path
        embedding = generate_image_embedding(image_path)

        # Save to database
        ProductEmbedding.objects.update_or_create(
            product=product,
            defaults={'embedding_vector': embedding.tolist()}
        )

        # Update FAISS index
        update_faiss_index(embedding.tolist(), product.id)
        
        logger.info(f"Successfully generated embedding for product {product_id}")

    except Product.DoesNotExist:
        logger.error(f"Product {product_id} not found.")
    except Exception as e:
        logger.error(f"Error generating embedding for product {product_id}: {e}")
