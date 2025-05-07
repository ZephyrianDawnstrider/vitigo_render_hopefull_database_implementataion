# stock_management/management/commands/populate_stock_data.py

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from user_management.models import CustomUser
from stock_management.models import (
    ItemCategory, StockItem, StockMovement, Supplier, PurchaseOrder, PurchaseOrderItem, StockAudit
)

class Command(BaseCommand):
    help = 'Generate sample stock management data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating sample stock management data...')

        # Create sample item categories if they don't exist
        categories = [
            {'name': 'Electronics', 'description': 'Electronic items'},
            {'name': 'Furniture', 'description': 'Furniture items'},
            {'name': 'Stationery', 'description': 'Stationery items'},
        ]
        for category in categories:
            ItemCategory.objects.get_or_create(
                name=category['name'],
                defaults={'description': category['description']}
            )

        # Create sample suppliers if they don't exist
        suppliers = [
            {'name': 'Supplier A', 'contact_person': 'John Doe', 'phone': '1234567890', 'email': 'john@example.com', 'address': '123 Main St, City, Country'},
            {'name': 'Supplier B', 'contact_person': 'Jane Smith', 'phone': '0987654321', 'email': 'jane@example.com', 'address': '456 Elm St, City, Country'},
        ]
        for supplier in suppliers:
            Supplier.objects.get_or_create(
                name=supplier['name'],
                defaults={
                    'contact_person': supplier['contact_person'],
                    'phone': supplier['phone'],
                    'email': supplier['email'],
                    'address': supplier['address'],
                    'is_active': True
                }
            )

        # Fetch all categories, suppliers, and users
        categories = ItemCategory.objects.all()
        suppliers = Supplier.objects.all()
        users = CustomUser.objects.all()

        # Create sample stock items
        stock_items = [
            {'name': 'Laptop', 'category': random.choice(categories), 'unit': 'PIECE', 'current_quantity': 50, 'reorder_point': 10, 'unit_price': Decimal('1000.00')},
            {'name': 'Office Chair', 'category': random.choice(categories), 'unit': 'PIECE', 'current_quantity': 30, 'reorder_point': 5, 'unit_price': Decimal('150.00')},
            {'name': 'Notebook', 'category': random.choice(categories), 'unit': 'PACK', 'current_quantity': 100, 'reorder_point': 20, 'unit_price': Decimal('5.00')},
        ]
        for item in stock_items:
            StockItem.objects.get_or_create(
                name=item['name'],
                defaults={
                    'category': item['category'],
                    'unit': item['unit'],
                    'current_quantity': item['current_quantity'],
                    'reorder_point': item['reorder_point'],
                    'unit_price': item['unit_price'],
                    'is_active': True
                }
            )

        # Fetch all stock items
        stock_items = StockItem.objects.all()

        # Generate sample stock movements
        for _ in range(20):  # Generate 20 sample stock movements
            item = random.choice(stock_items)
            movement_type = random.choice(['IN', 'OUT'])
            quantity = random.randint(1, 10) if movement_type == 'IN' else -random.randint(1, 10)
            performed_by = random.choice(users)
            StockMovement.objects.create(
                item=item,
                quantity=quantity,
                movement_type=movement_type,
                performed_by=performed_by,
                notes='Sample stock movement'
            )

        # Generate sample purchase orders
        for _ in range(10):  # Generate 10 sample purchase orders
            supplier = random.choice(suppliers)
            created_by = random.choice(users)
            total_amount = Decimal('0.00')
            purchase_order = PurchaseOrder.objects.create(
                supplier=supplier,
                status=random.choice(['DRAFT', 'SUBMITTED', 'APPROVED', 'ORDERED', 'RECEIVED', 'CANCELLED']),
                total_amount=total_amount,
                created_by=created_by
            )
            for _ in range(random.randint(1, 5)):  # Add 1 to 5 items to each purchase order
                item = random.choice(stock_items)
                quantity = random.randint(1, 10)
                unit_price = item.unit_price
                total_amount += unit_price * quantity
                PurchaseOrderItem.objects.create(
                    purchase_order=purchase_order,
                    item=item,
                    quantity=quantity,
                    unit_price=unit_price
                )
            purchase_order.total_amount = total_amount
            purchase_order.save()

        # Generate sample stock audits
        for item in stock_items:
            StockAudit.objects.create(
                item=item,
                expected_quantity=item.current_quantity,
                actual_quantity=item.current_quantity + random.randint(-5, 5),
                discrepancy=random.randint(-5, 5),
                performed_by=random.choice(users),
                notes='Sample stock audit'
            )

        self.stdout.write(self.style.SUCCESS('Successfully generated sample stock management data'))