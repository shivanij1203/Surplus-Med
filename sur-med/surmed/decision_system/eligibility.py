from django.utils import timezone
from .models import Supply, EligibilityRule


def run_eligibility_check(supply):
    """Returns (is_eligible, details_dict) for a supply."""
    rules = EligibilityRule.objects.filter(is_active=True)
    checks = []
    warnings = []

    for rule in rules:
        if rule.rule_type == 'EXPIRY_DATE':
            checks.append(_check_expiry(supply, rule))
        elif rule.rule_type == 'CATEGORY':
            checks.append(_check_category(supply, rule))
        elif rule.rule_type == 'PACKAGING':
            checks.append(_check_packaging(supply, rule))
        elif rule.rule_type == 'QUANTITY':
            checks.append(_check_quantity(supply, rule))
        elif rule.rule_type == 'DOCUMENTATION':
            checks.append(_check_documentation(supply, rule))

    # warnings
    if supply.days_until_expiry and supply.days_until_expiry < 90:
        warnings.append(f"Short shelf life: Only {supply.days_until_expiry} days until expiry.")
    if supply.packaging_status in ['OPENED_INTACT', 'MINOR_DAMAGE', 'SIGNIFICANT_DAMAGE']:
        warnings.append(f"Packaging concern: {supply.get_packaging_status_display()}.")
    if supply.storage_conditions == 'UNKNOWN':
        warnings.append("Storage conditions unknown.")
    if not supply.batch_number:
        warnings.append("No batch number provided.")

    blocking_failed = [c for c in checks if c.get('is_blocking') and not c['passed']]
    is_eligible = len(blocking_failed) == 0
    passed_count = sum(1 for c in checks if c['passed'])

    details = {
        'is_eligible': is_eligible,
        'checks': checks,
        'warnings': warnings,
        'summary': f"Passed {passed_count}/{len(checks)} checks" if is_eligible
                   else f"Failed {len(blocking_failed)} blocking checks",
    }

    return is_eligible, details


def _check_expiry(supply, rule):
    if supply.is_expired:
        return _fail(rule, f"Expired (expiry: {supply.expiry_date})")

    if rule.min_shelf_life_days:
        days = supply.days_until_expiry
        if days < rule.min_shelf_life_days:
            return _fail(rule, f"{days} days remaining, need {rule.min_shelf_life_days}")

    return _pass(rule, f"{supply.days_until_expiry} days remaining")


def _check_category(supply, rule):
    if not rule.allowed_categories:
        return _pass(rule, "No restrictions")
    if supply.category not in rule.allowed_categories:
        return _fail(rule, f"'{supply.category}' not allowed")
    return _pass(rule, f"'{supply.category}' is allowed")


def _check_packaging(supply, rule):
    if not rule.required_packaging_status:
        return _pass(rule, "No requirements")
    if supply.packaging_status not in rule.required_packaging_status:
        return _fail(rule, f"'{supply.packaging_status}' does not meet requirements")
    return _pass(rule, f"'{supply.packaging_status}' acceptable")


def _check_quantity(supply, rule):
    if rule.min_quantity and supply.quantity < rule.min_quantity:
        return _fail(rule, f"Quantity {supply.quantity} below minimum {rule.min_quantity}")
    if rule.max_quantity and supply.quantity > rule.max_quantity:
        return _fail(rule, f"Quantity {supply.quantity} exceeds maximum {rule.max_quantity}")
    return _pass(rule, f"Quantity {supply.quantity} OK")


def _check_documentation(supply, rule):
    count = supply.evidence_set.count()
    if count == 0:
        return _fail(rule, "No evidence provided")
    has_photos = supply.evidence_set.filter(evidence_type__startswith='PHOTO_').exists()
    if not has_photos:
        return {
            'name': rule.name, 'passed': not rule.is_blocking,
            'message': "No photo evidence", 'is_blocking': rule.is_blocking
        }
    return _pass(rule, f"{count} evidence items provided")


def _pass(rule, msg):
    return {'name': rule.name, 'passed': True, 'message': msg, 'is_blocking': rule.is_blocking}


def _fail(rule, msg):
    return {'name': rule.name, 'passed': False, 'message': msg, 'is_blocking': rule.is_blocking}
