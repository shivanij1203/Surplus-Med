from django.utils import timezone
from typing import Dict, List, Tuple
from .models import Supply, EligibilityRule


class EligibilityCheck:

    def __init__(self, name: str, passed: bool, message: str = "", is_blocking: bool = True):
        self.name = name
        self.passed = passed
        self.message = message
        self.is_blocking = is_blocking

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'passed': self.passed,
            'message': self.message,
            'is_blocking': self.is_blocking
        }


class EligibilityResult:

    def __init__(self):
        self.checks: List[EligibilityCheck] = []
        self.warnings: List[str] = []

    def add_check(self, check: EligibilityCheck):
        self.checks.append(check)

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    @property
    def is_eligible(self) -> bool:
        return all(check.passed for check in self.checks if check.is_blocking)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> Dict:
        return {
            'is_eligible': self.is_eligible,
            'checks': [check.to_dict() for check in self.checks],
            'warnings': self.warnings,
            'summary': self.get_summary()
        }

    def get_summary(self) -> str:
        passed = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)

        if self.is_eligible:
            return f"Eligible: Passed {passed}/{total} checks"
        else:
            return f"Ineligible: Failed {total - passed} blocking checks"


class EligibilityEngine:

    def __init__(self):
        self.rules = EligibilityRule.objects.filter(is_active=True)

    def evaluate(self, supply: Supply) -> EligibilityResult:
        result = EligibilityResult()

        for rule in self.rules:
            if rule.rule_type == 'EXPIRY_DATE':
                check = self._check_expiry_date(supply, rule)
            elif rule.rule_type == 'CATEGORY':
                check = self._check_category(supply, rule)
            elif rule.rule_type == 'PACKAGING':
                check = self._check_packaging(supply, rule)
            elif rule.rule_type == 'QUANTITY':
                check = self._check_quantity(supply, rule)
            elif rule.rule_type == 'DOCUMENTATION':
                check = self._check_documentation(supply, rule)
            else:
                    continue

            if check:
                result.add_check(check)

        self._add_warnings(supply, result)

        return result

    def _check_expiry_date(self, supply: Supply, rule: EligibilityRule) -> EligibilityCheck:

        if supply.is_expired:
            return EligibilityCheck(
                name=rule.name,
                passed=False,
                message=f"Supply is expired (expiry date: {supply.expiry_date})",
                is_blocking=rule.is_blocking
            )

        if rule.min_shelf_life_days:
            days_remaining = supply.days_until_expiry

            if days_remaining < rule.min_shelf_life_days:
                return EligibilityCheck(
                    name=rule.name,
                    passed=False,
                    message=f"Insufficient shelf life: {days_remaining} days remaining (minimum: {rule.min_shelf_life_days} days)",
                    is_blocking=rule.is_blocking
                )

        return EligibilityCheck(
            name=rule.name,
            passed=True,
            message=f"Valid expiry date: {supply.days_until_expiry} days remaining",
            is_blocking=rule.is_blocking
        )

    def _check_category(self, supply: Supply, rule: EligibilityRule) -> EligibilityCheck:

        if not rule.allowed_categories:
            return EligibilityCheck(
                name=rule.name,
                passed=True,
                message="No category restrictions",
                is_blocking=rule.is_blocking
            )

        allowed = rule.allowed_categories

        if supply.category not in allowed:
            return EligibilityCheck(
                name=rule.name,
                passed=False,
                message=f"Category '{supply.category}' is not in allowed list: {', '.join(allowed)}",
                is_blocking=rule.is_blocking
            )

        return EligibilityCheck(
            name=rule.name,
            passed=True,
            message=f"Category '{supply.category}' is allowed",
            is_blocking=rule.is_blocking
        )

    def _check_packaging(self, supply: Supply, rule: EligibilityRule) -> EligibilityCheck:

        if not rule.required_packaging_status:
            return EligibilityCheck(
                name=rule.name,
                passed=True,
                message="No packaging requirements",
                is_blocking=rule.is_blocking
            )

        required_statuses = rule.required_packaging_status

        if supply.packaging_status not in required_statuses:
            return EligibilityCheck(
                name=rule.name,
                passed=False,
                message=f"Packaging status '{supply.packaging_status}' does not meet requirements",
                is_blocking=rule.is_blocking
            )

        return EligibilityCheck(
            name=rule.name,
            passed=True,
            message=f"Packaging status '{supply.packaging_status}' is acceptable",
            is_blocking=rule.is_blocking
        )

    def _check_quantity(self, supply: Supply, rule: EligibilityRule) -> EligibilityCheck:

        if rule.min_quantity and supply.quantity < rule.min_quantity:
            return EligibilityCheck(
                name=rule.name,
                passed=False,
                message=f"Quantity {supply.quantity} below minimum {rule.min_quantity}",
                is_blocking=rule.is_blocking
            )

        if rule.max_quantity and supply.quantity > rule.max_quantity:
            return EligibilityCheck(
                name=rule.name,
                passed=False,
                message=f"Quantity {supply.quantity} exceeds maximum {rule.max_quantity}",
                is_blocking=rule.is_blocking
            )

        return EligibilityCheck(
            name=rule.name,
            passed=True,
            message=f"Quantity {supply.quantity} is within acceptable limits",
            is_blocking=rule.is_blocking
        )

    def _check_documentation(self, supply: Supply, rule: EligibilityRule) -> EligibilityCheck:

        evidence_count = supply.evidence_set.count()

        if evidence_count == 0:
            return EligibilityCheck(
                name=rule.name,
                passed=False,
                message="No evidence documentation provided",
                is_blocking=rule.is_blocking
            )

        photo_evidence = supply.evidence_set.filter(
            evidence_type__startswith='PHOTO_'
        ).exists()

        if not photo_evidence:
            return EligibilityCheck(
                name=rule.name,
                passed=False if rule.is_blocking else True,
                message="No photographic evidence provided",
                is_blocking=rule.is_blocking
            )

        return EligibilityCheck(
            name=rule.name,
            passed=True,
            message=f"{evidence_count} evidence items provided",
            is_blocking=rule.is_blocking
        )

    def _add_warnings(self, supply: Supply, result: EligibilityResult):

        if supply.days_until_expiry and supply.days_until_expiry < 90:
            result.add_warning(
                f"Short shelf life: Only {supply.days_until_expiry} days until expiry. "
                "High-priority redistribution recommended."
            )

        if supply.packaging_status in ['OPENED_INTACT', 'MINOR_DAMAGE', 'SIGNIFICANT_DAMAGE']:
            result.add_warning(
                f"Packaging integrity concern: {supply.get_packaging_status_display()}. "
                "Additional review recommended."
            )

        if supply.storage_conditions == 'UNKNOWN':
            result.add_warning(
                "Storage conditions unknown. Verify with submitter before final decision."
            )

        if not supply.batch_number:
            result.add_warning(
                "No batch number provided. Traceability may be limited."
            )


def run_eligibility_check(supply: Supply) -> Tuple[bool, Dict]:
    """
    Convenience function to run eligibility check on a supply.

    Returns:
        Tuple of (is_eligible: bool, details: dict)
    """
    engine = EligibilityEngine()
    result = engine.evaluate(supply)
    return result.is_eligible, result.to_dict()
