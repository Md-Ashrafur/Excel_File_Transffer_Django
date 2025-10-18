# excel_transfer/views.py
import os
from django.http import HttpResponse
from django.conf import settings
import pandas as pd
from .models import Customer, Product, Order
from django.db import transaction
from datetime import datetime

from .models import UploadRecord
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render


def transfer_data(request):
    """
    Reads three Excel files from the project's excel_folder:
      - customers.xlsx
      - products.xlsx
      - orders.xlsx

    Assumptions: each file has a header row and exactly 5 columns which map to the model fields:
    customers -> [customer_id, name, email, phone, address]
    products  -> [product_id, name, category, price, stock]
    orders    -> [order_id, customer_id, product_id, quantity, order_date]
    """

    base_dir = settings.BASE_DIR  # project root
    excel_dir = os.path.join(base_dir, 'excel_folder')

    # full paths
    customers_file = os.path.join(excel_dir, 'customers.xlsx')
    products_file = os.path.join(excel_dir, 'products.xlsx')
    orders_file = os.path.join(excel_dir, 'orders.xlsx')

    try:
        # Read Excel files with pandas
        df_customers = pd.read_excel(customers_file)
        df_products = pd.read_excel(products_file)
        df_orders = pd.read_excel(orders_file)
    except Exception as e:
        return HttpResponse(f"Error reading excel files: {e}", status=500)

    # Normalize column names (strip spaces)
    df_customers.columns = [str(c).strip() for c in df_customers.columns]
    df_products.columns = [str(c).strip() for c in df_products.columns]
    df_orders.columns = [str(c).strip() for c in df_orders.columns]

    # Map columns by position to the expected names (safe if headers vary):
    # If your Excel headers match exact names, you can use them instead.
    try:
        # customers - take first 5 columns
        cust_cols = list(df_customers.columns[:5])
        cust_rows = []
        for _, r in df_customers.iterrows():
            vals = [r.iloc[i] if i < len(r) else None for i in range(5)]
            customer = Customer(
                customer_id=str(vals[0]) if not pd.isna(vals[0]) else '',
                name=str(vals[1]) if not pd.isna(vals[1]) else '',
                email=str(vals[2]) if not pd.isna(vals[2]) else None,
                phone=str(vals[3]) if not pd.isna(vals[3]) else None,
                address=str(vals[4]) if not pd.isna(vals[4]) else None,
            )
            cust_rows.append(customer)

        # products
        prod_rows = []
        for _, r in df_products.iterrows():
            vals = [r.iloc[i] if i < len(r) else None for i in range(5)]
            # safe conversions
            price = None
            try:
                price = float(vals[3]) if not pd.isna(vals[3]) else 0
            except:
                price = 0
            stock = None
            try:
                stock = int(vals[4]) if not pd.isna(vals[4]) else 0
            except:
                stock = 0

            product = Product(
                product_id=str(vals[0]) if not pd.isna(vals[0]) else '',
                name=str(vals[1]) if not pd.isna(vals[1]) else '',
                category=str(vals[2]) if not pd.isna(vals[2]) else None,
                price=price,
                stock=stock,
            )
            prod_rows.append(product)

        # orders
        order_rows = []
        for _, r in df_orders.iterrows():
            vals = [r.iloc[i] if i < len(r) else None for i in range(5)]
            quantity = 1
            try:
                quantity = int(vals[3]) if not pd.isna(vals[3]) else 1
            except:
                quantity = 1

            # parse date if possible
            order_date = None
            if not pd.isna(vals[4]):
                try:
                    if isinstance(vals[4], (pd.Timestamp, datetime)):
                        order_date = vals[4].date()
                    else:
                        order_date = pd.to_datetime(vals[4]).date()
                except Exception:
                    order_date = None

            order = Order(
                order_id=str(vals[0]) if not pd.isna(vals[0]) else '',
                customer_id=str(vals[1]) if not pd.isna(vals[1]) else '',
                product_id=str(vals[2]) if not pd.isna(vals[2]) else '',
                quantity=quantity,
                order_date=order_date,
            )
            order_rows.append(order)

        # Use transaction and bulk_create
        with transaction.atomic():
            # Optional: clear existing rows (uncomment if you want fresh load)
            # Customer.objects.all().delete()
            # Product.objects.all().delete()
            # Order.objects.all().delete()

            # Bulk create but avoid duplicates for unique fields: here we will upsert-like by checking existence.
            # Simpler approach: try bulk_create and catch IntegrityError for duplicates OR
            # we clear tables then bulk_create. For safe default I'll attempt upsert per row.

            # Upsert customers
            for c in cust_rows:
                Customer.objects.update_or_create(customer_id=c.customer_id, defaults={
                    'name': c.name,
                    'email': c.email,
                    'phone': c.phone,
                    'address': c.address
                })

            # Upsert products
            for p in prod_rows:
                Product.objects.update_or_create(product_id=p.product_id, defaults={
                    'name': p.name,
                    'category': p.category,
                    'price': p.price,
                    'stock': p.stock
                })

            # Upsert orders
            for o in order_rows:
                Order.objects.update_or_create(order_id=o.order_id, defaults={
                    'customer_id': o.customer_id,
                    'product_id': o.product_id,
                    'quantity': o.quantity,
                    'order_date': o.order_date
                })

    except Exception as e:
        return HttpResponse(f"Error during processing/DB operation: {e}", status=500)

    return HttpResponse("Data transfer successful", status=200)


def upload_files(request):
    """
    GET: render upload form
    POST: accept three files (input names: file1, file2, file3), save them under excel_folder,
          record their filename and size (bytes) in UploadRecord and render success info.
    """

    # ensure excel_folder exists
    base_dir = settings.BASE_DIR
    excel_dir = os.path.join(base_dir, 'excel_folder')
    os.makedirs(excel_dir, exist_ok=True)

    if request.method == 'POST':
        f1 = request.FILES.get('file1')
        f2 = request.FILES.get('file2')
        f3 = request.FILES.get('file3')

        # helper to save file and return filename and size
        def save_uploaded(f):
            if not f:
                return None, None
            # secure filename: use original name as-is; you can sanitize if needed
            dest_path = os.path.join(excel_dir, f.name)
            # if you want to avoid overwriting, append timestamp or unique suffix
            with open(dest_path, 'wb') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            size_bytes = os.path.getsize(dest_path)
            return f.name, size_bytes

        name1, size1 = save_uploaded(f1)
        name2, size2 = save_uploaded(f2)
        name3, size3 = save_uploaded(f3)

        # save record in DB
        rec = UploadRecord.objects.create(
            file1_name=name1,
            file1_size=size1,
            file2_name=name2,
            file2_size=size2,
            file3_name=name3,
            file3_size=size3
        )

        # render success page listing sizes in human-friendly form
        def human(n):
            if not n:
                return ''
            # convert bytes to readable
            for unit in ['B','KB','MB','GB','TB']:
                if n < 1024.0:
                    return f"{n:3.1f} {unit}"
                n /= 1024.0
            return f"{n:.1f} PB"

        context = {
            'record': rec,
            'file1_human': human(size1),
            'file2_human': human(size2),
            'file3_human': human(size3),
        }
        return render(request, 'upload_success.html', context)

    # GET -> render upload form
    return render(request, 'upload.html')