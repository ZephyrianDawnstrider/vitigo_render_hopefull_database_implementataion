import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from asset_management.models import (
    AssetCategory, Asset, MaintenanceSchedule, 
    AssetDepreciation, AssetAudit, InsurancePolicy
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populate sample data for asset management module'

    def __init__(self):
        super().__init__()
        self.categories = []
        self.assets = []
        self.status_choices = [status[0] for status in Asset.STATUS_CHOICES]
        self.condition_choices = [condition[0] for condition in Asset.CONDITION_CHOICES]
        self.current_date = timezone.now()

    def add_arguments(self, parser):
        parser.add_argument(
            '--categories',
            type=int,
            default=5,
            help='Number of asset categories to create'
        )
        parser.add_argument(
            '--assets',
            type=int,
            default=50,
            help='Number of assets to create'
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write('Starting asset data population...')
            
            # Clear existing data
            self._clear_existing_data()
            
            # Create sample data
            with transaction.atomic():
                self._create_categories(options['categories'])
                self._create_assets(options['assets'])
                self._create_maintenance_schedules()
                self._create_depreciation_records()
                self._create_audits()
                self._create_insurance_policies()

            self.stdout.write(self.style.SUCCESS('Successfully populated asset data'))
            
        except Exception as e:
            logger.error(f"Failed to populate asset data: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Failed to populate asset data: {str(e)}'))

    def _clear_existing_data(self):
        """Clear all existing asset-related data"""
        try:
            with transaction.atomic():
                InsurancePolicy.objects.all().delete()
                AssetAudit.objects.all().delete()
                AssetDepreciation.objects.all().delete()
                MaintenanceSchedule.objects.all().delete()
                Asset.objects.all().delete()
                AssetCategory.objects.all().delete()
            logger.info("Successfully cleared existing asset data")
        except Exception as e:
            logger.error(f"Error clearing existing data: {str(e)}")
            raise

    def _create_categories(self, count):
        """Create sample asset categories"""
        try:
            categories = [
                ('MED', 'Medical Equipment', 20),
                ('IT', 'IT Equipment', 33),
                ('OFF', 'Office Equipment', 15),
                ('VEH', 'Vehicles', 25),
                ('LAB', 'Laboratory Equipment', 30),
                ('FUR', 'Furniture', 10),
                ('SEC', 'Security Equipment', 20)
            ]

            for i in range(min(count, len(categories))):
                code, name, dep_rate = categories[i]
                category = AssetCategory.objects.create(
                    name=name,
                    code=code,
                    description=f"Sample description for {name}",
                    depreciation_rate=dep_rate,
                    expected_lifetime_years=random.randint(5, 10),
                    maintenance_frequency_days=random.choice([30, 90, 180, 365])
                )
                self.categories.append(category)
                logger.info(f"Created category: {category.name}")
        except Exception as e:
            logger.error(f"Error creating categories: {str(e)}")
            raise

    def _create_assets(self, count):
        """Create sample assets"""
        try:
            manufacturers = ['MedTech', 'HealthCorp', 'BioSystems', 'TechPro', 'LabEquip']
            locations = ['Main Building', 'Annex', 'Laboratory', 'Clinic', 'Storage']

            for i in range(count):
                purchase_date = self.current_date - timedelta(days=random.randint(1, 730))
                asset = Asset.objects.create(
                    name=f"Asset {i+1}",
                    asset_id=f"AST{i+1:04d}",
                    category=random.choice(self.categories),
                    description=f"Sample asset description {i+1}",
                    model_number=f"MOD{random.randint(1000, 9999)}",
                    serial_number=f"SER{random.randint(10000, 99999)}",
                    manufacturer=random.choice(manufacturers),
                    purchase_date=purchase_date,
                    purchase_cost=Decimal(random.randint(1000, 50000)),
                    warranty_expiry=purchase_date + timedelta(days=365*3),
                    vendor=f"Vendor {random.randint(1, 5)}",
                    status=random.choice(self.status_choices),
                    condition=random.choice(self.condition_choices),
                    location=random.choice(locations),
                    specifications={
                        "power": f"{random.randint(100, 1000)}W",
                        "weight": f"{random.randint(5, 100)}kg",
                        "dimensions": f"{random.randint(30, 200)}x{random.randint(30, 200)}cm"
                    }
                )
                self.assets.append(asset)
                logger.info(f"Created asset: {asset.name}")
        except Exception as e:
            logger.error(f"Error creating assets: {str(e)}")
            raise

    def _create_maintenance_schedules(self):
        """Create sample maintenance schedules"""
        try:
            for asset in random.sample(self.assets, len(self.assets) // 2):
                MaintenanceSchedule.objects.create(
                    asset=asset,
                    maintenance_type=random.choice(['Preventive', 'Corrective', 'Calibration']),
                    description=f"Scheduled maintenance for {asset.name}",
                    scheduled_date=self.current_date + timedelta(days=random.randint(1, 90)),
                    priority=random.choice(['HIGH', 'MEDIUM', 'LOW']),
                    estimated_duration_hours=Decimal(random.randint(1, 8)),
                    status=random.choice(['SCHEDULED', 'IN_PROGRESS', 'COMPLETED']),
                    cost_estimate=Decimal(random.randint(100, 1000))
                )
            logger.info("Created maintenance schedules")
        except Exception as e:
            logger.error(f"Error creating maintenance schedules: {str(e)}")
            raise

    def _create_depreciation_records(self):
        """Create sample depreciation records"""
        try:
            current_fiscal_year = str(self.current_date.year)
            for asset in self.assets:
                initial_value = asset.purchase_cost
                # Convert depreciation_rate to Decimal to avoid float multiplication
                depreciation_rate = Decimal(str(asset.category.depreciation_rate / 100))
                
                for year in range(asset.purchase_date.year, self.current_date.year + 1):
                    # Ensure decimal operations
                    depreciation_amount = (initial_value * depreciation_rate).quantize(Decimal('0.01'))
                    current_value = (initial_value - depreciation_amount).quantize(Decimal('0.01'))
                    
                    AssetDepreciation.objects.create(
                        asset=asset,
                        date=datetime(year, 12, 31),
                        current_value=current_value,
                        depreciation_amount=depreciation_amount,
                        fiscal_year=str(year)
                    )
                    initial_value = current_value
            logger.info("Created depreciation records")
        except Exception as e:
            logger.error(f"Error creating depreciation records: {str(e)}")
            raise

    def _create_audits(self):
        """Create sample asset audits"""
        try:
            for asset in random.sample(self.assets, len(self.assets) // 3):
                AssetAudit.objects.create(
                    asset=asset,
                    audit_date=self.current_date - timedelta(days=random.randint(1, 180)),
                    location_verified=random.choice([True, False]),
                    condition_verified=random.choice([True, False]),
                    discrepancies="" if random.random() > 0.3 else "Some discrepancies found",
                    status=random.choice(['PLANNED', 'IN_PROGRESS', 'COMPLETED']),
                    conducted_by=f"Auditor {random.randint(1, 5)}",
                    verified_by=f"Supervisor {random.randint(1, 3)}",
                    photos=[]
                )
            logger.info("Created asset audits")
        except Exception as e:
            logger.error(f"Error creating asset audits: {str(e)}")
            raise

    def _create_insurance_policies(self):
        """Create sample insurance policies"""
        try:
            providers = ['InsureCo', 'SafeGuard', 'AssetProtect', 'SecureAssets']
            
            for asset in random.sample(self.assets, len(self.assets) // 4):
                start_date = self.current_date - timedelta(days=random.randint(1, 180))
                # Convert multipliers to Decimal
                coverage_multiplier = Decimal('1.2')
                premium_multiplier = Decimal('0.05')
                deductible_multiplier = Decimal('0.1')
                
                InsurancePolicy.objects.create(
                    asset=asset,
                    policy_number=f"POL{random.randint(10000, 99999)}",
                    provider=random.choice(providers),
                    coverage_type=random.choice(['Full Coverage', 'Basic', 'Premium']),
                    coverage_amount=(asset.purchase_cost * coverage_multiplier).quantize(Decimal('0.01')),
                    premium_amount=(asset.purchase_cost * premium_multiplier).quantize(Decimal('0.01')),
                    start_date=start_date,
                    end_date=start_date + timedelta(days=365),
                    deductible=(asset.purchase_cost * deductible_multiplier).quantize(Decimal('0.01')),
                    status='ACTIVE'
                )
            logger.info("Created insurance policies")
        except Exception as e:
            logger.error(f"Error creating insurance policies: {str(e)}")
            raise
