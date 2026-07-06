from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from main.forms import LoginForm, OrderForm, RegisterForm
from main.models import Book, Order


def index(request):
    books = Book.objects.all()
    paginator = Paginator(books, 9)
    page = request.GET.get("page")
    books_page = paginator.get_page(page)
    return render(request, "shop/index.html", {"books": books_page})


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, "shop/book_detail.html", {"book": book})


def register(request):
    if request.user.is_authenticated:
        return redirect("index")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Регистрация прошла успешно. Добро пожаловать!")
            return redirect("index")
    else:
        form = RegisterForm()
    return render(request, "shop/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("index")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Вы успешно вошли в систему.")
            return redirect("index")
    else:
        form = LoginForm()
    return render(request, "shop/login.html", {"form": form})


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "Вы вышли из системы.")
    return redirect("index")


@login_required
def order_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data["quantity"]
            if quantity > book.stock:
                messages.error(request, "Недостаточно товара на складе.")
            else:
                Order.objects.create(buyer=request.user, book=book, quantity=quantity)
                book.stock -= quantity
                book.save(update_fields=["stock"])
                messages.success(request, "Заказ успешно оформлен!")
                return redirect("my_orders")
    else:
        form = OrderForm()
    return render(request, "shop/order.html", {"book": book, "form": form})


@login_required
def my_orders(request):
    orders = Order.objects.filter(buyer=request.user).select_related("book")
    return render(request, "shop/orders.html", {"orders": orders})
