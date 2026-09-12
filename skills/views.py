from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import Tier
from accounts.tiers import require_tier, team_member_ids

from .forms import (
    CertificateSubmitForm,
    RecordCertificateForm,
    RecordSkillForm,
    SelfReportForm,
)
from .models import CertificateAward, SkillProficiency

User = get_user_model()


@login_required
def me(request):
    proficiencies = request.user.proficiencies.select_related(
        "skill", "skill__category"
    ).order_by("skill__category__name", "skill__name")
    certificates = request.user.certificate_awards.select_related(
        "certificate", "recorded_by"
    )
    return render(
        request,
        "skills/me.html",
        {
            "proficiencies": proficiencies,
            "certificates": certificates,
            "self_report_form": SelfReportForm(),
            "certificate_form": CertificateSubmitForm(),
        },
    )


@login_required
def self_assess(request):
    form = SelfReportForm(request.POST or None)
    if form.is_valid():
        skill = form.cleaned_data["skill"]
        existing = SkillProficiency.objects.filter(
            user=request.user, skill=skill
        ).first()
        if existing and existing.reported_by_id != request.user.id:
            messages.error(
                request,
                f"Your {skill} rating was recorded by a manager and can't be "
                "edited here — ask them to update it.",
            )
        else:
            if existing:
                existing.level = form.cleaned_data["level"]
                existing.evidence = form.cleaned_data["evidence"]
                existing.status = SkillProficiency.Status.PENDING
                existing.approved_by = None
                existing.reported_by = request.user
                existing.save()
                messages.info(request, f"Updated {skill} — pending approval.")
            else:
                SkillProficiency.objects.create(
                    user=request.user,
                    skill=skill,
                    level=form.cleaned_data["level"],
                    evidence=form.cleaned_data["evidence"],
                    status=SkillProficiency.Status.PENDING,
                    reported_by=request.user,
                )
                messages.info(request, f"Submitted {skill} — pending approval.")
            return redirect(reverse("my_skills"))
    return render(request, "skills/me.html", {"self_report_form": form})


@login_required
def submit_certificate(request):
    form = CertificateSubmitForm(request.POST or None)
    if form.is_valid():
        form.instance.user = request.user
        form.instance.recorded_by = request.user
        form.save()
        messages.info(request, "Certificate submitted — pending approval.")
        return redirect(reverse("my_skills"))
    return render(request, "skills/me.html", {"certificate_form": form})


@require_tier("team_manager")
def record_skill(request):
    form = RecordSkillForm(request.POST or None)
    if form.is_valid():
        member = form.cleaned_data["user"]
        allowed = team_member_ids(request.user)
        if member.id not in allowed:
            return HttpResponseForbidden("That user isn't on a team you manage.")
        skill = form.cleaned_data["skill"]
        existing = SkillProficiency.objects.filter(user=member, skill=skill).first()
        if existing:
            existing.level = form.cleaned_data["level"]
            existing.evidence = form.cleaned_data["evidence"]
            existing.status = SkillProficiency.Status.APPROVED
            existing.reported_by = request.user
            existing.approved_by = request.user
            existing.save()
        else:
            SkillProficiency.objects.create(
                user=member,
                skill=skill,
                level=form.cleaned_data["level"],
                evidence=form.cleaned_data["evidence"],
                status=SkillProficiency.Status.APPROVED,
                reported_by=request.user,
                approved_by=request.user,
            )
        messages.success(request, f"Recorded {skill} for {member.username}.")
        return redirect(reverse("team_list"))
    messages.error(request, form.errors)
    return redirect(reverse("team_list"))


@require_tier("team_manager")
def record_certificate(request):
    form = RecordCertificateForm(request.POST or None)
    if form.is_valid():
        member = form.cleaned_data["user"]
        allowed = team_member_ids(request.user)
        if member.id not in allowed:
            return HttpResponseForbidden("That user isn't on a team you manage.")
        form.instance.recorded_by = request.user
        form.instance.approved_by = request.user
        form.instance.status = CertificateAward.Status.APPROVED
        award = form.save()
        messages.success(request, f"Recorded {award.certificate} for {member.username}.")
        return redirect(reverse("team_list"))
    messages.error(request, form.errors)
    return redirect(reverse("team_list"))


def _resolve_approval(request, pk, award=False):
    obj = get_object_or_404(
        CertificateAward if award else SkillProficiency, pk=pk
    )
    if request.user.tier == Tier.LEADERSHIP:
        return obj
    if obj.user_id not in set(team_member_ids(request.user)):
        return None
    return obj


@require_tier("team_manager", "leadership")
def approvals(request):
    if request.user.tier == Tier.LEADERSHIP:
        member_ids = User.objects.values_list("id", flat=True)
    else:
        member_ids = team_member_ids(request.user)

    pending_skills = (
        SkillProficiency.objects.filter(status=SkillProficiency.Status.PENDING, user_id__in=member_ids)
        .select_related("user", "skill", "skill__category")
        .order_by("user__username", "skill__name")
    )
    pending_certificates = (
        CertificateAward.objects.filter(status=CertificateAward.Status.PENDING, user_id__in=member_ids)
        .select_related("user", "certificate")
        .order_by("user__username", "-created_at")
    )
    return render(
        request,
        "skills/approvals.html",
        {
            "pending_skills": pending_skills,
            "pending_certificates": pending_certificates,
        },
    )


@require_tier("team_manager", "leadership")
def approve_proficiency(request, pk):
    obj = _resolve_approval(request, pk)
    if obj is None:
        return HttpResponseForbidden("Not on a team you manage.")
    obj.status = SkillProficiency.Status.APPROVED
    obj.approved_by = request.user
    obj.save()
    messages.success(request, f"Approved {obj.skill} for {obj.user.username}.")
    return redirect(reverse("approvals"))


@require_tier("team_manager", "leadership")
def reject_proficiency(request, pk):
    obj = _resolve_approval(request, pk)
    if obj is None:
        return HttpResponseForbidden("Not on a team you manage.")
    obj.status = SkillProficiency.Status.REJECTED
    obj.approved_by = request.user
    obj.save()
    messages.warning(request, f"Rejected {obj.skill} for {obj.user.username}.")
    return redirect(reverse("approvals"))


@require_tier("team_manager", "leadership")
def approve_certificate(request, pk):
    obj = _resolve_approval(request, pk, award=True)
    if obj is None:
        return HttpResponseForbidden("Not on a team you manage.")
    obj.status = CertificateAward.Status.APPROVED
    obj.approved_by = request.user
    obj.save()
    SkillProficiency.objects.update_or_create(
        user=obj.user,
        skill=obj.skill,
        defaults={
            "level": obj.level,
            "status": SkillProficiency.Status.APPROVED,
            "reported_by": obj.user,
            "approved_by": request.user,
            "evidence": f"Certified via {obj.certificate} ({obj.obtained_on}).",
        },
    )
    messages.success(
        request,
        f"Approved {obj.certificate} for {obj.user.username} and updated their {obj.skill} rating.",
    )
    return redirect(reverse("approvals"))


@require_tier("team_manager", "leadership")
def reject_certificate(request, pk):
    obj = _resolve_approval(request, pk, award=True)
    if obj is None:
        return HttpResponseForbidden("Not on a team you manage.")
    obj.status = CertificateAward.Status.REJECTED
    obj.approved_by = request.user
    obj.save()
    messages.warning(request, f"Rejected {obj.certificate} for {obj.user.username}.")
    return redirect(reverse("approvals"))