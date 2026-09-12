from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy

from accounts.forms import SignupForm
from accounts.models import Tier


@login_required
def home(request):
    if request.user.tier == Tier.TEAM_MANAGER:
        return redirect(reverse("team_list"))
    if request.user.tier == Tier.LEADERSHIP:
        return redirect(reverse("project_list"))
    return redirect(reverse("my_skills"))


def register(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse_lazy("home"))
    else:
        form = SignupForm()
    return render(request, "registration/register.html", {"form": form})