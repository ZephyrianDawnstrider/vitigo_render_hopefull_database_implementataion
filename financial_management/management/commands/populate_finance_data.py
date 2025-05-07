# financial_management/management/commands/populate_finance_data.py

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from user_management.models import CustomUser
from patient_management.models import Patient
from financial_management.models import (
    GSTRate, Invoice, InvoiceItem, Payment, Expense, TDSEntry, FinancialYear, FinancialReport
)

class Command(BaseCommand):
    help = 'Generate sample finance management data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating sample finance management data...')

        # Create sample GST rates if they don't exist
        gst_rates = [
            {'rate': Decimal('5.00'), 'description': 'Reduced Rate'},
            {'rate': Decimal('12.00'), 'description': 'Standard Rate'},
            {'rate': Decimal('18.00'), 'description': 'Higher Rate'},
        ]
        for rate in gst_rates:
            GSTRate.objects.get_or_create(
                rate=rate['rate'],
                defaults={'description': rate['description']}
            )

        # Fetch all GST rates, patients, and users
        gst_rates = GSTRate.objects.all()
        patients = Patient.objects.all()
        users = CustomUser.objects.all()

        # Create sample invoices
        for _ in range(10):  # Generate 10 sample invoices
            patient = random.choice(patients)
            created_by = random.choice(users)
            invoice_date = timezone.now().date() - timezone.timedelta(days=random.randint(0, 30))
            due_date = invoice_date + timezone.timedelta(days=30)
            total_amount = Decimal('0.00')
            invoice = Invoice.objects.create(
                patient=patient,
                invoice_number=f"INV-{random.randint(1000, 9999)}",
                invoice_date=invoice_date,
                due_date=due_date,
                status=random.choice(['DRAFT', 'ISSUED', 'PAID', 'CANCELLED']),
                total_amount=total_amount,
                total_with_gst=total_amount,
                created_by=created_by
            )
            for _ in range(random.randint(1, 5)):  # Add 1 to 5 items to each invoice
                description = f"Service {random.randint(1, 100)}"
                quantity = random.randint(1, 10)
                unit_price = Decimal(random.randint(100, 1000))
                gst_rate = random.choice(gst_rates)
                total_price = quantity * unit_price
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    gst_rate=gst_rate,
                    total_price=total_price
                )
                total_amount += total_price
            invoice.total_amount = total_amount
            invoice.total_with_gst = total_amount * Decimal('1.18')  # Assuming 18% GST for simplicity
            invoice.save()

        # Create sample payments
        invoices = Invoice.objects.all()
        for invoice in invoices:
            if invoice.status == 'PAID':
                Payment.objects.create(
                    invoice=invoice,
                    amount=invoice.total_with_gst,
                    payment_date=timezone.now(),
                    payment_method=random.choice(['CASH', 'UPI', 'NEFT', 'CREDIT_CARD', 'DEBIT_CARD', 'CHEQUE']),
                    received_by=random.choice(users)
                )

        # Create sample expenses
        expense_categories = ['RENT', 'UTILITIES', 'SALARIES', 'SUPPLIES', 'EQUIPMENT', 'MAINTENANCE', 'MARKETING', 'OTHER']
        for _ in range(10):  # Generate 10 sample expenses
            category = random.choice(expense_categories)
            amount = Decimal(random.randint(1000, 10000))
            gst_amount = amount * Decimal('0.18')  # Assuming 18% GST for simplicity
            total_amount = amount + gst_amount
            Expense.objects.create(
                category=category,
                amount=amount,
                gst_amount=gst_amount,
                total_amount=total_amount,
                date=timezone.now().date() - timezone.timedelta(days=random.randint(0, 30)),
                description=f"{category} expense",
                vendor=f"Vendor {random.randint(1, 100)}",
                payment_method=random.choice(['CASH', 'UPI', 'NEFT', 'CREDIT_CARD', 'DEBIT_CARD', 'CHEQUE']),
                created_by=random.choice(users),
                approved_by=random.choice(users)
            )

        # Create sample TDS entries
        expenses = Expense.objects.all()
        for expense in expenses:
            TDSEntry.objects.create(
                expense=expense,
                tds_rate=random.choice([0.1, 1, 2, 5, 10]),
                tds_amount=expense.amount * Decimal('0.01'),  # Assuming 1% TDS for simplicity
                date_deducted=timezone.now().date()
            )

        # Create sample financial years
        for year in range(2020, 2023):  # Generate financial years from 2020 to 2022
            FinancialYear.objects.get_or_create(
                start_date=timezone.datetime(year, 4, 1).date(),
                end_date=timezone.datetime(year + 1, 3, 31).date(),
                defaults={'is_current': year == 2022}
            )

        # Create sample financial reports
        financial_years = FinancialYear.objects.all()
        for year in financial_years:
            FinancialReport.objects.create(
                report_type='YEARLY',
                start_date=year.start_date,
                end_date=year.end_date,
                financial_year=year,
                total_revenue=Decimal(random.randint(100000, 500000)),
                total_expenses=Decimal(random.randint(50000, 200000)),
                net_profit=Decimal(random.randint(50000, 300000)),
                total_gst_collected=Decimal(random.randint(10000, 50000)),
                total_tds_deducted=Decimal(random.randint(5000, 20000)),
                generated_by=random.choice(users)
            )

        self.stdout.write(self.style.SUCCESS('Successfully generated sample finance management data'))