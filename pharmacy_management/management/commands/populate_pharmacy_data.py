from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from pharmacy_management.models import (
    Medication, MedicationStock, Supplier,
    PurchaseOrder, PurchaseOrderItem
)
from decimal import Decimal
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Populate sample data for pharmacy management system'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.medications_data = [
            {
                'name': 'Amoxicillin',
                'generic_name': 'Amoxicillin',
                'description': 'Antibiotic medication',
                'dosage_form': 'Capsule',
                'strength': '500mg',
                'manufacturer': 'PharmaCorp',
                'price': Decimal('15.99'),
                'requires_prescription': True
            },
            {
                'name': 'Paracetamol',
                'generic_name': 'Acetaminophen',
                'description': 'Pain reliever and fever reducer',
                'dosage_form': 'Tablet',
                'strength': '500mg',
                'manufacturer': 'HealthCare Ltd',
                'price': Decimal('5.99'),
                'requires_prescription': False
            },
            {
                'name': 'Lisinopril',
                'generic_name': 'Lisinopril',
                'description': 'ACE inhibitor for blood pressure control',
                'dosage_form': 'Tablet',
                'strength': '10mg',
                'manufacturer': 'MedPharm',
                'price': Decimal('25.50'),
                'requires_prescription': True
            },
            {
                'name': 'Metformin',
                'generic_name': 'Metformin HCl',
                'description': 'Oral diabetes medicine',
                'dosage_form': 'Tablet',
                'strength': '850mg',
                'manufacturer': 'DiabeCare',
                'price': Decimal('12.75'),
                'requires_prescription': True
            },
            {
                'name': 'Ibuprofen',
                'generic_name': 'Ibuprofen',
                'description': 'NSAID pain reliever',
                'dosage_form': 'Tablet',
                'strength': '400mg',
                'manufacturer': 'PainRelief Inc',
                'price': Decimal('8.99'),
                'requires_prescription': False
            },
            {
                'name': 'Omeprazole',
                'generic_name': 'Omeprazole',
                'description': 'Proton pump inhibitor',
                'dosage_form': 'Capsule',
                'strength': '20mg',
                'manufacturer': 'GastroHealth',
                'price': Decimal('18.50'),
                'requires_prescription': True
            },
            {
                'name': 'Cetirizine',
                'generic_name': 'Cetirizine HCl',
                'description': 'Antihistamine for allergies',
                'dosage_form': 'Tablet',
                'strength': '10mg',
                'manufacturer': 'AllergyMed',
                'price': Decimal('9.99'),
                'requires_prescription': False
            },
            {
                'name': 'Salbutamol',
                'generic_name': 'Albuterol',
                'description': 'Bronchodilator',
                'dosage_form': 'Inhaler',
                'strength': '100mcg',
                'manufacturer': 'RespiraCare',
                'price': Decimal('35.00'),
                'requires_prescription': True
            },
            {
                'name': 'Vitamin D3',
                'generic_name': 'Cholecalciferol',
                'description': 'Vitamin D supplement',
                'dosage_form': 'Tablet',
                'strength': '1000IU',
                'manufacturer': 'VitaHealth',
                'price': Decimal('7.50'),
                'requires_prescription': False
            },
            {
                'name': 'Sertraline',
                'generic_name': 'Sertraline HCl',
                'description': 'SSRI antidepressant',
                'dosage_form': 'Tablet',
                'strength': '50mg',
                'manufacturer': 'MentalCare',
                'price': Decimal('28.99'),
                'requires_prescription': True
            }
        ]

        self.suppliers_data = [
            {
                'name': 'MedSupply Co',
                'contact_person': 'John Doe',
                'email': 'john@medsupply.com',
                'phone': '123-456-7890',
                'address': '123 Medical Street, Healthcare City'
            },
            {
                'name': 'PharmaCorp International',
                'contact_person': 'Jane Smith',
                'email': 'jane@pharmacorp.com',
                'phone': '098-765-4321',
                'address': '456 Pharma Avenue, Medicine Town'
            },
        ]

    def create_admin_user(self):
        try:
            admin_user, created = User.objects.get_or_create(
                email='admin@example.com',
                defaults={'password': 'admin123', 'is_superuser': True, 'is_staff': True}
            )
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
            else:
                self.stdout.write(self.style.SUCCESS('Admin user already exists'))
            return admin_user
        except Exception as e:
            logger.error(f'Error creating admin user: {str(e)}')
            raise

    @transaction.atomic
    def create_medications(self):
        created_medications = []
        try:
            for med_data in self.medications_data:
                medication = Medication.objects.create(**med_data)
                created_medications.append(medication)
                
                # Create corresponding stock
                MedicationStock.objects.create(
                    medication=medication,
                    quantity=100,
                    reorder_level=20
                )
            self.stdout.write(self.style.SUCCESS(f'Created {len(created_medications)} medications with stock'))
            return created_medications
        except Exception as e:
            logger.error(f'Error creating medications: {str(e)}')
            raise

    @transaction.atomic
    def create_suppliers(self):
        created_suppliers = []
        try:
            for supplier_data in self.suppliers_data:
                supplier = Supplier.objects.create(**supplier_data)
                created_suppliers.append(supplier)
            self.stdout.write(self.style.SUCCESS(f'Created {len(created_suppliers)} suppliers'))
            return created_suppliers
        except Exception as e:
            logger.error(f'Error creating suppliers: {str(e)}')
            raise

    @transaction.atomic
    def create_purchase_orders(self, admin_user, medications, suppliers):
        try:
            for supplier in suppliers:
                po = PurchaseOrder.objects.create(
                    supplier=supplier,
                    status='ORDERED',
                    total_amount=Decimal('0'),
                    expected_delivery_date=datetime.now().date() + timedelta(days=7),
                    created_by=admin_user
                )

                total_amount = Decimal('0')
                for medication in medications[:2]:  # Create items for first two medications
                    quantity = 50
                    unit_price = medication.price
                    total_amount += quantity * unit_price

                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        medication=medication,
                        quantity=quantity,
                        unit_price=unit_price
                    )

                po.total_amount = total_amount
                po.save()

            self.stdout.write(self.style.SUCCESS('Created purchase orders with items'))
        except Exception as e:
            logger.error(f'Error creating purchase orders: {str(e)}')
            raise

    def handle(self, *args, **options):
        try:
            self.stdout.write('Starting to populate pharmacy data...')
            
            # Clear existing data
            self.stdout.write('Clearing existing data...')
            PurchaseOrderItem.objects.all().delete()
            PurchaseOrder.objects.all().delete()
            MedicationStock.objects.all().delete()
            Medication.objects.all().delete()
            Supplier.objects.all().delete()

            # Create new data
            with transaction.atomic():
                admin_user = self.create_admin_user()
                medications = self.create_medications()
                suppliers = self.create_suppliers()
                self.create_purchase_orders(admin_user, medications, suppliers)

            self.stdout.write(self.style.SUCCESS('Successfully populated all pharmacy data'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to populate data: {str(e)}'))
            logger.error(f'Population script failed: {str(e)}')
            raise
