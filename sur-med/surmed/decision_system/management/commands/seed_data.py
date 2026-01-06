from django.core.management.base import BaseCommand
from decision_system.models import ReasonCode, EligibilityRule


class Command(BaseCommand):
    help = 'Seed initial reason codes and eligibility rules for the decision system'

    def handle(self, *args, **options):
        self.stdout.write('Seeding reason codes...')
        self.create_reason_codes()

        self.stdout.write('Seeding eligibility rules...')
        self.create_eligibility_rules()

        self.stdout.write(self.style.SUCCESS('Successfully seeded all data!'))

    def create_reason_codes(self):
        reason_codes = [
            {
                'code': 'ACC-001',
                'decision_type': 'ACCEPTED',
                'description': 'Meets all safety and eligibility criteria. Sealed packaging, valid expiry, proper documentation.'
            },
            {
                'code': 'ACC-002',
                'decision_type': 'ACCEPTED',
                'description': 'Acceptable with minor packaging concerns. Supply is safe for redistribution with appropriate handling.'
            },
            {
                'code': 'ACC-003',
                'decision_type': 'ACCEPTED',
                'description': 'Priority acceptance due to high demand and short shelf life. Immediate redistribution recommended.'
            },
            {
                'code': 'REV-001',
                'decision_type': 'REVIEW',
                'description': 'Insufficient documentation provided. Additional evidence required before final decision.'
            },
            {
                'code': 'REV-002',
                'decision_type': 'REVIEW',
                'description': 'Packaging integrity concerns. Physical inspection required before acceptance.'
            },
            {
                'code': 'REV-003',
                'decision_type': 'REVIEW',
                'description': 'Storage conditions unclear. Need verification of proper handling before acceptance.'
            },
            {
                'code': 'REV-004',
                'decision_type': 'REVIEW',
                'description': 'Category requires specialist review. Escalating to senior reviewer.'
            },
            {
                'code': 'REJ-001',
                'decision_type': 'REJECTED',
                'description': 'Expired supply. Cannot accept items past expiry date for safety reasons.'
            },
            {
                'code': 'REJ-002',
                'decision_type': 'REJECTED',
                'description': 'Insufficient shelf life. Less than minimum required days until expiry.'
            },
            {
                'code': 'REJ-003',
                'decision_type': 'REJECTED',
                'description': 'Damaged or compromised packaging. Safety and sterility cannot be guaranteed.'
            },
            {
                'code': 'REJ-004',
                'decision_type': 'REJECTED',
                'description': 'Prescription medication. System does not accept controlled pharmaceutical drugs.'
            },
            {
                'code': 'REJ-005',
                'decision_type': 'REJECTED',
                'description': 'Incomplete or missing batch information. Traceability requirements not met.'
            },
            {
                'code': 'REJ-006',
                'decision_type': 'REJECTED',
                'description': 'Category not accepted. Item type outside program scope.'
            },
        ]

        for rc_data in reason_codes:
            ReasonCode.objects.get_or_create(
                code=rc_data['code'],
                defaults={
                    'decision_type': rc_data['decision_type'],
                    'description': rc_data['description'],
                    'is_active': True
                }
            )
            self.stdout.write(f'  Created/verified reason code: {rc_data["code"]}')

    def create_eligibility_rules(self):
        rules = [
            {
                'name': 'Minimum Shelf Life - 60 Days',
                'rule_type': 'EXPIRY_DATE',
                'description': 'Supply must have at least 60 days remaining until expiry to ensure adequate time for redistribution.',
                'is_blocking': True,
                'min_shelf_life_days': 60
            },
            {
                'name': 'No Prescription Drugs',
                'rule_type': 'CATEGORY',
                'description': 'Prescription medications and controlled substances are explicitly excluded from acceptance.',
                'is_blocking': True,
                'allowed_categories': ['PPE', 'SURGICAL', 'DIAGNOSTIC', 'WOUND_CARE', 'EQUIPMENT', 'OTHER_SUPPLIES']
            },
            {
                'name': 'Packaging Integrity - No Significant Damage',
                'rule_type': 'PACKAGING',
                'description': 'Packaging must be sealed/unopened or have only minor acceptable damage to ensure product safety.',
                'is_blocking': True,
                'required_packaging_status': ['SEALED_UNOPENED', 'OPENED_INTACT', 'MINOR_DAMAGE']
            },
            {
                'name': 'Photo Evidence Required',
                'rule_type': 'DOCUMENTATION',
                'description': 'At least one photographic evidence of packaging, label, or product is required for verification.',
                'is_blocking': False
            },
            {
                'name': 'Quantity Minimum - 1 Unit',
                'rule_type': 'QUANTITY',
                'description': 'At least one unit must be submitted.',
                'is_blocking': True,
                'min_quantity': 1
            },
        ]

        for rule_data in rules:
            EligibilityRule.objects.get_or_create(
                name=rule_data['name'],
                defaults=rule_data
            )
            self.stdout.write(f'  Created/verified rule: {rule_data["name"]}')
