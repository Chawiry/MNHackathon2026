from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import DevelopmentActivityForm, ExperienceEntryForm, PerformanceReviewForm


def _render_invalid(request, form, title):
    return render(request, "profiles/form_error.html", {"form": form, "title": title})


@login_required
def add_activity(request):
    form = DevelopmentActivityForm(request.POST or None)
    if form.is_valid():
        form.instance.user = request.user
        form.save()
        messages.success(request, "Development activity saved.")
        return redirect(reverse("my_skills"))
    return _render_invalid(request, form, "Development activity")


@login_required
def add_experience(request):
    form = ExperienceEntryForm(request.POST or None)
    if form.is_valid():
        form.instance.user = request.user
        form.save()
        messages.success(request, "Experience entry saved.")
        return redirect(reverse("my_skills"))
    return _render_invalid(request, form, "Experience entry")


@login_required
def add_review(request):
    form = PerformanceReviewForm(request.POST or None)
    if form.is_valid():
        form.instance.user = request.user
        form.save()
        messages.success(request, "Performance review saved.")
        return redirect(reverse("my_skills"))
    return _render_invalid(request, form, "Performance review")