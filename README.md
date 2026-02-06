# Ecommerce Image Search API

AI-powered REST API for visual product search in ecommerce. This platform allows users to find products by uploading images, utilizing deep learning (ResNet50) for feature extraction and FAISS for efficient similarity search.

## 🚀 Features

- **Visual Search**: Upload an image to find visually similar products in the catalog.
- **Deep Learning Integration**: Uses pre-trained ResNet50 for 2048-dimensional image embeddings.
- **Vector Search**: FAISS (Facebook AI Similarity Search) integration for high-performance similarity matching.
- **Smart Cart System**: Manage products with automatic handling of duplicates and active cart state.
- **Checkout & Orders**: Full ordering workflow including tax calculation and cart freezing.
- **Robust Auth**: JWT-based authentication using `dj-rest-auth` and `allauth`.
- **Admin Dashboard**: Comprehensive management of products, categories, and orders.
- **Background Tasks**: Celery/Redis for asynchronous embedding generation.

## 🛠 Tech Stack

- **Backend**: Django, Django REST Framework
- **Deep Learning**: PyTorch, Torchvision (ResNet50)
- **Vector Index**: FAISS (CPU)
- **Database**: PostgreSQL
- **Worker/Broker**: Celery, Redis
- **Auth**: JWT, dj-rest-auth, allauth
- **Documentation**: Swagger/OpenAPI (drf-yasg)

## 📡 API Endpoints

### Authentication
- `POST /auth/registration/`: Register a new account
- `POST /auth/login/`: Login and receive JWT keys
- `POST /auth/logout/`: Logout
- `POST /auth/token/refresh/`: Refresh access token
- `POST /auth/user/`: Get/Update current user profile

### Products & Search
- `GET /api/v1/products/`: List all products (supports filtering)
- `GET /api/v1/products/{id}/`: Product details
- `POST /api/v1/products/create/`: Create NEW product (Admin only)
- `PUT/DELETE /api/v1/products/{id}/`: Modify/Delete product (Admin only)
- `POST /api/v1/products/search/upload/`: **Image Search** (Upload image to find similar items)
- `GET /api/v1/products/category/{slug}/`: List products by category
- `GET /api/v1/categories/`: List all categories

### Cart
- `GET /api/v1/cart/active/`: View your active cart and totals
- `GET /api/v1/cart/items/`: List items in the cart
- `POST /api/v1/cart/items/`: Add product to cart
- `PATCH /api/v1/cart/items/{id}/`: Update item quantity
- `DELETE /api/v1/cart/items/{id}/`: Remove item from cart
- `DELETE /api/v1/cart/clear/`: Clear entire active cart

### Orders
- `GET /api/v1/orders/`: List your order history
- `POST /api/v1/orders/`: **Checkout** (Creates order from active cart)
- `GET /api/v1/orders/{id}/`: Order details
- `PUT /api/v1/orders/{id}/cancel/`: Cancel a pending order
- `GET /api/v1/orders/{id}/items/`: List items in a specific order

## 🔧 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/stephenoba/ecommerce-image-search-api.git
   cd ecommerce-image-search-api
   ```

2. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

3. **Seed the database** (Optional):
   ```bash
   docker-compose exec web python manage.py seed_db
   ```

4. **Build the FAISS search index**:
   ```bash
   docker-compose exec web python manage.py rebuild_index
   ```

## 🔍 Management Commands

- `python manage.py seed_db`: Populates the DB with dummy categories, products, and images.
- `python manage.py rebuild_index`: Processes all product images to build/refresh the `faiss_index.bin` file.

## 🧪 Testing

Run the full test suite (37+ tests covering search, cart, and orders):
```bash
docker-compose exec web python manage.py test
```

---

## ERD
![ERD](https://github.com/stephenoba/ecommerce-image-search-api/blob/main/erd.jpeg)