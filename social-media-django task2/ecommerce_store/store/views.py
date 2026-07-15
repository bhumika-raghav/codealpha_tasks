from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from store.cart import Cart
from store.forms import CartAddProductForm, OrderCreateForm, RegisterForm
from store.models import Category, Order, OrderItem, Product


def product_list(request, category_slug=None):
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True)

    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    return render(request, 'store/product_list.html', {
        'categories': categories,
        'products': products,
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart_product_form = CartAddProductForm()
    return render(request, 'store/product_detail.html', {
        'product': product,
        'cart_product_form': cart_product_form,
    })


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product=product, quantity=cd['quantity'], update_quantity=False)
        messages.success(request, f'{product.name} cart me add ho gaya.')
    return redirect('cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.info(request, f'{product.name} cart se remove kar diya gaya.')
    return redirect('cart_detail')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'store/cart.html', {'cart': cart})


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Account ban gaya! Welcome to ShopEasy.')
            return redirect('product_list')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, 'Aapka cart khaali hai.')
        return redirect('product_list')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity'],
                )
            cart.clear()
            return redirect('order_success', order_id=order.id)
    else:
        form = OrderCreateForm()

    return render(request, 'store/checkout.html', {'cart': cart, 'form': form})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})


@login_required
def order_history(request):
    orders = request.user.orders.all()
    return render(request, 'store/order_history.html', {'orders': orders})


class MyLoginView(LoginView):
    template_name = 'registration/login.html'


class MyLogoutView(LogoutView):
    next_page = 'product_list'
