# excel_transfer/models.py
from django.db import models

class Customer(models.Model):
    # assuming Excel has: customer_id, name, email, phone, address
    customer_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.customer_id} - {self.name}"


class Product(models.Model):
    # assuming Excel has: product_id, name, category, price, stock
    product_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=200, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product_id} - {self.name}"


class Order(models.Model):
    # assuming Excel has: order_id, customer_id, product_id, quantity, order_date
    order_id = models.CharField(max_length=100, unique=True)
    customer_id = models.CharField(max_length=100)   # could be FK but kept CharField for simplicity
    product_id = models.CharField(max_length=100)
    quantity = models.IntegerField(default=1)
    order_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.order_id}"
    
   # excel_transfer/models.py


# --- your existing models: Customer, Product, Order (keep them) ---

class UploadRecord(models.Model):
    file1_name = models.CharField(max_length=255, blank=True, null=True)
    file1_size = models.BigIntegerField(blank=True, null=True)   # size in bytes
    file2_name = models.CharField(max_length=255, blank=True, null=True)
    file2_size = models.BigIntegerField(blank=True, null=True)
    file3_name = models.CharField(max_length=255, blank=True, null=True)
    file3_size = models.BigIntegerField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload #{self.pk} at {self.uploaded_at}"
 
