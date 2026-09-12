from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from accounts.forms import SignupForm


@login_required
def home(request):
    return render(request, "core/home.html")


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