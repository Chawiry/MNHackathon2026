from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, reverse

from accounts.models import Tier


@login_required
def home(request):
    if request.user.tier == Tier.TEAM_MANAGER:
        return redirect(reverse("team_list"))
    if request.user.tier == Tier.LEADERSHIP:
        return redirect(reverse("project_list"))
    return redirect(reverse("my_skills"))