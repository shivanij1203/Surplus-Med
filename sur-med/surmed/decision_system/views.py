from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from io import BytesIO

from .models import Supply, Decision, Evidence, ReasonCode, EligibilityRule, AuditLog
from .eligibility import EligibilityEngine, run_eligibility_check


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit(action, user=None, supply=None, decision=None, request=None, details=None):
    """Helper function to log audit events"""
    AuditLog.objects.create(
        action=action,
        user=user,
        supply=supply,
        decision=decision,
        ip_address=get_client_ip(request) if request else None,
        details=details or {}
    )


@login_required
def dashboard(request):
    """
    Main dashboard for healthcare reviewers.
    Shows pending supplies, statistics, and recent decisions.
    """
    stats = {
        'pending_review': Supply.objects.filter(
            decision_status__in=['PENDING_INITIAL', 'PENDING_FINAL']
        ).count(),
        'accepted': Supply.objects.filter(decision_status='ACCEPTED').count(),
        'needs_review': Supply.objects.filter(decision_status='NEEDS_REVIEW').count(),
        'rejected': Supply.objects.filter(decision_status='REJECTED').count(),
    }

    pending_supplies = Supply.objects.filter(
        decision_status__in=['PENDING_INITIAL', 'PENDING_FINAL', 'NEEDS_REVIEW']
    ).select_related('submitted_by').order_by('-submitted_date')[:20]

    recent_decisions = Decision.objects.select_related(
        'supply', 'decided_by', 'reason_code'
    ).order_by('-decision_date')[:10]

    context = {
        'stats': stats,
        'pending_supplies': pending_supplies,
        'recent_decisions': recent_decisions,
    }

    return render(request, 'decision_system/dashboard.html', context)


@login_required
def supply_submit(request):
    """
    Handle supply submission with evidence upload.
    Creates supply record and runs initial eligibility checks.
    """
    if request.method == 'POST':
        supply = Supply(
            item_name=request.POST.get('item_name'),
            category=request.POST.get('category'),
            quantity=int(request.POST.get('quantity')),
            unit=request.POST.get('unit'),
            expiry_date=request.POST.get('expiry_date'),
            batch_number=request.POST.get('batch_number', ''),
            description=request.POST.get('description', ''),
            packaging_status=request.POST.get('packaging_status'),
            storage_conditions=request.POST.get('storage_conditions'),
            submitted_by=request.user,
            decision_status='PENDING_INITIAL'
        )
        supply.save()

        evidence_count = 0
        for key in request.POST.keys():
            if key.startswith('evidence_type_'):
                index = key.split('_')[-1]
                evidence_type = request.POST.get(f'evidence_type_{index}')
                evidence_file = request.FILES.get(f'evidence_file_{index}')
                evidence_description = request.POST.get(f'evidence_description_{index}', '')

                if evidence_type and evidence_file:
                    Evidence.objects.create(
                        supply=supply,
                        evidence_type=evidence_type,
                        file=evidence_file,
                        description=evidence_description,
                        uploaded_by=request.user
                    )
                    evidence_count += 1

        log_audit(
            action='SUPPLY_SUBMITTED',
            user=request.user,
            supply=supply,
            request=request,
            details={
                'supply_id': supply.supply_id,
                'item_name': supply.item_name,
                'evidence_count': evidence_count
            }
        )

        messages.success(
            request,
            f'Supply {supply.supply_id} submitted successfully. {evidence_count} evidence files uploaded.'
        )
        return redirect('decision_system:supply_detail', pk=supply.id)

    context = {
        'today': timezone.now().date()
    }
    return render(request, 'decision_system/supply_submit.html', context)


@login_required
def supply_review(request, pk):
    """
    Display supply details for review with eligibility assessment.
    Shows all evidence, decision history, and eligibility check results.
    """
    supply = get_object_or_404(Supply, pk=pk)

    engine = EligibilityEngine()
    eligibility_result = engine.evaluate(supply)

    reason_codes = ReasonCode.objects.filter(is_active=True)

    context = {
        'supply': supply,
        'eligibility': eligibility_result.to_dict(),
        'reason_codes': reason_codes,
    }

    return render(request, 'decision_system/supply_review.html', context)


@login_required
def supply_decide(request, pk):
    """
    Process decision submission for a supply.
    Creates immutable decision record and updates supply status.
    """
    if request.method != 'POST':
        return redirect('decision_system:supply_review', pk=pk)

    supply = get_object_or_404(Supply, pk=pk)

    decision_type = request.POST.get('decision')
    reason_code_id = request.POST.get('reason_code')
    justification = request.POST.get('justification')
    notes = request.POST.get('notes', '')

    if not all([decision_type, reason_code_id, justification]):
        messages.error(request, 'All required fields must be filled.')
        return redirect('decision_system:supply_review', pk=pk)

    reason_code = get_object_or_404(ReasonCode, pk=reason_code_id)

    is_eligible, eligibility_details = run_eligibility_check(supply)

    if request.user.is_staff:
        decision_level = 'FINAL'
    else:
        decision_level = 'INITIAL'

    decision = Decision.objects.create(
        supply=supply,
        decision=decision_type,
        decision_level=decision_level,
        reason_code=reason_code,
        justification=justification,
        notes=notes,
        decided_by=request.user,
        eligibility_passed=is_eligible,
        eligibility_details=eligibility_details
    )

    log_audit(
        action='DECISION_MADE',
        user=request.user,
        supply=supply,
        decision=decision,
        request=request,
        details={
            'decision': decision_type,
            'reason_code': reason_code.code,
            'decision_level': decision_level
        }
    )

    messages.success(
        request,
        f'Decision recorded: {decision.get_decision_display()} for {supply.supply_id}'
    )

    return redirect('decision_system:decision_detail', pk=decision.id)


@login_required
def supply_list(request):
    """List all supplies with filtering and search"""
    supplies = Supply.objects.select_related('submitted_by').all()

    status_filter = request.GET.get('status')
    if status_filter:
        supplies = supplies.filter(decision_status=status_filter)

    category_filter = request.GET.get('category')
    if category_filter:
        supplies = supplies.filter(category=category_filter)

    search_query = request.GET.get('search')
    if search_query:
        supplies = supplies.filter(
            Q(supply_id__icontains=search_query) |
            Q(item_name__icontains=search_query) |
            Q(batch_number__icontains=search_query)
        )

    paginator = Paginator(supplies, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
    }

    return render(request, 'decision_system/supply_list.html', context)


@login_required
def supply_detail(request, pk):
    """Display detailed view of a single supply"""
    supply = get_object_or_404(Supply, pk=pk)

    is_eligible, eligibility_details = run_eligibility_check(supply)

    context = {
        'supply': supply,
        'eligibility': eligibility_details,
    }

    return render(request, 'decision_system/supply_detail.html', context)


@login_required
def decision_detail(request, pk):
    """Display full details of a decision record"""
    decision = get_object_or_404(
        Decision.objects.select_related('supply', 'decided_by', 'reason_code'),
        pk=pk
    )

    context = {
        'decision': decision,
    }

    return render(request, 'decision_system/decision_detail.html', context)


@login_required
def audit_log(request):
    """Display audit log with filtering capabilities"""
    decisions = Decision.objects.select_related(
        'supply', 'decided_by', 'reason_code'
    ).all()

    filters = {}

    date_from = request.GET.get('date_from')
    if date_from:
        decisions = decisions.filter(decision_date__gte=date_from)
        filters['date_from'] = date_from

    date_to = request.GET.get('date_to')
    if date_to:
        decisions = decisions.filter(decision_date__lte=date_to)
        filters['date_to'] = date_to

    decision_type = request.GET.get('decision_type')
    if decision_type:
        decisions = decisions.filter(decision=decision_type)
        filters['decision_type'] = decision_type

    search = request.GET.get('search')
    if search:
        decisions = decisions.filter(
            Q(supply__supply_id__icontains=search) |
            Q(supply__item_name__icontains=search) |
            Q(reason_code__code__icontains=search)
        )
        filters['search'] = search

    audit_stats = {
        'total_decisions': decisions.count(),
        'accepted_count': decisions.filter(decision='ACCEPTED').count(),
        'review_count': decisions.filter(decision='REVIEW').count(),
        'rejected_count': decisions.filter(decision='REJECTED').count(),
    }

    paginator = Paginator(decisions, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'decisions': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'filters': filters,
        'audit_stats': audit_stats,
    }

    return render(request, 'decision_system/audit_log.html', context)


@login_required
def export_audit(request):
    """Export audit data in CSV or PDF format"""
    export_format = request.GET.get('format', 'csv')

    decisions = Decision.objects.select_related(
        'supply', 'decided_by', 'reason_code'
    ).all()

    date_from = request.GET.get('date_from')
    if date_from:
        decisions = decisions.filter(decision_date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        decisions = decisions.filter(decision_date__lte=date_to)

    decision_type = request.GET.get('decision_type')
    if decision_type:
        decisions = decisions.filter(decision=decision_type)

    log_audit(
        action='EXPORT_GENERATED',
        user=request.user,
        request=request,
        details={
            'format': export_format,
            'record_count': decisions.count()
        }
    )

    if export_format == 'csv':
        return export_audit_csv(decisions)
    elif export_format == 'pdf':
        return export_audit_pdf(decisions)
    else:
        return HttpResponse('Invalid format', status=400)


def export_audit_csv(decisions):
    """Export audit records to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="audit_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Decision Date',
        'Supply ID',
        'Item Name',
        'Decision',
        'Reason Code',
        'Decided By',
        'Decision Level',
        'Eligibility Passed',
        'Justification'
    ])

    for decision in decisions:
        writer.writerow([
            decision.decision_date.strftime('%Y-%m-%d %H:%M:%S'),
            decision.supply.supply_id,
            decision.supply.item_name,
            decision.get_decision_display(),
            decision.reason_code.code,
            decision.decided_by.username,
            decision.get_decision_level_display(),
            'Yes' if decision.eligibility_passed else 'No',
            decision.justification
        ])

    return response


def export_audit_pdf(decisions):
    """Export audit records to PDF"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
    except ImportError:
        return HttpResponse('PDF export requires reportlab library', status=500)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    title = Paragraph("Surplus Med Audit Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    metadata = Paragraph(
        f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
        f"Total Records: {decisions.count()}",
        styles['Normal']
    )
    elements.append(metadata)
    elements.append(Spacer(1, 20))

    data = [['Date', 'Supply ID', 'Item', 'Decision', 'Decided By']]

    for decision in decisions:
        data.append([
            decision.decision_date.strftime('%Y-%m-%d'),
            decision.supply.supply_id,
            decision.supply.item_name[:30],
            decision.get_decision_display(),
            decision.decided_by.username
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="audit_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response


@login_required
def manage_rules(request):
    """Manage eligibility rules (staff only)"""
    if not request.user.is_staff:
        messages.error(request, 'Only staff can manage eligibility rules.')
        return redirect('decision_system:dashboard')

    rules = EligibilityRule.objects.all()

    context = {
        'rules': rules,
    }

    return render(request, 'decision_system/manage_rules.html', context)


def user_login(request):
    """Handle user login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('decision_system:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'decision_system/login.html')


@login_required
def user_logout(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('decision_system:login')
