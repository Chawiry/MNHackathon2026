from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.tiers import require_tier

from .forms import CreateUserForm
from .models import Tier, User


@require_tier("leadership")
def user_list(request):
    users = (
        User.objects.order_by("is_active", "username")
        .prefetch_related("team_memberships__team")
    )
    return render(
        request,
        "accounts/user_list.html",
        {"users": users, "tiers": Tier.choices},
    )


@require_tier("leadership")
def create_user(request):
    form = CreateUserForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        messages.success(
            request,
            f"Created account for {user.username} ({user.get_tier_display()}).",
        )
        return redirect(reverse("user_list"))
    return render(request, "accounts/create_user.html", {"form": form})


@require_tier("leadership")
def change_tier(request, pk):
    user = get_object_or_404(User, pk=pk)
    tier = request.POST.get("tier")
    if tier in Tier.values:
        user.tier = tier
        user.save(update_fields=["tier"])
        messages.success(
            request, f"{user.username} is now {Tier(tier).label}."
        )
    return redirect(reverse("user_list"))


@require_tier("leadership")
def toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, "You can't deactivate your own account.")
        return redirect(reverse("user_list"))
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    messages.success(
        request,
        f"{user.username} {'reactivated' if user.is_active else 'deactivated'}.",
    )
    return redirect(reverse("user_list"))