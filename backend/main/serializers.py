from django.contrib.auth.models import User
from rest_framework import serializers

from main.models import Book, Order


class BookSerializer(serializers.ModelSerializer):
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "author", "description", "price", "stock", "cover", "in_stock"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class OrderSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "book", "quantity", "created_at"]


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["book", "quantity"]

    def validate(self, attrs):
        book = attrs["book"]
        quantity = attrs["quantity"]
        if quantity > book.stock:
            raise serializers.ValidationError({"quantity": "Not enough stock available."})
        return attrs

    def create(self, validated_data):
        book = validated_data["book"]
        quantity = validated_data["quantity"]
        order = Order.objects.create(
            buyer=self.context["request"].user, book=book, quantity=quantity
        )
        book.stock -= quantity
        book.save(update_fields=["stock"])
        return order
