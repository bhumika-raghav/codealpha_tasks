# ShopEasy — Django E-commerce Store

A simple e-commerce demo built with Django. Features:
- Product listing with images, category filter, search
- Product detail page
- Session-based shopping cart (add/remove, quantity)
- User registration & login
- Checkout with shipping details → creates an Order
- Order history for logged-in users
- Django admin to manage products, categories, and orders (upload images here)

## Setup

1. Extract this project and open the folder in VS Code / terminal.

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   venv\Scripts\activate      (Windows)
   source venv/bin/activate   (Mac/Linux)
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create database tables:
   ```
   python manage.py makemigrations
   python manage.py migrate
   ```

5. Create an admin (superuser) account:
   ```
   python manage.py createsuperuser
   ```

6. Run the server:
   ```
   python manage.py runserver
   ```

7. Open the site: http://127.0.0.1:8000/

## Adding products (with images)

1. Go to http://127.0.0.1:8000/admin/ and log in with your superuser account.
2. Under **Store → Categories**, add a category (e.g. "Electronics").
3. Under **Store → Products**, click **Add Product**, fill in name, price, stock,
   choose a category, and upload an image. Save.
4. The product will now appear on the homepage with its image.

## Project Structure

```
ecommerce_store/
├── manage.py
├── requirements.txt
├── ecommerce/          # project settings, root urls
├── store/               # main app: models, views, templates, static files
│   ├── models.py        # Category, Product, Order, OrderItem
│   ├── views.py          # product list/detail, cart, checkout, auth
│   ├── cart.py            # session-based cart logic
│   ├── templates/
│   └── static/
└── media/               # uploaded product images (created automatically)
```

## Notes

- This uses SQLite by default (`db.sqlite3`), no extra database setup needed.
- Product images are stored in `media/products/` and served automatically
  while `DEBUG = True`.
- For production use, set `DEBUG = False`, add a real `SECRET_KEY`, and
  configure proper static/media file serving.
