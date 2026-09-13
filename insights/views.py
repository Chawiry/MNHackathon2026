from django.shortcuts import render

from accounts.tiers import require_tier

from . import services


@require_tier("leadership")
def insights_dashboard(request):
    return render(
        request,
        "insights/insights.html",
        {
            "bottlenecks": services.at_risk_skills(),
            "stays": services.expected_stays(),
            "depletion": services.skill_depletion(),
            "successors": services.successors(),
            "months_per_level": services.MONTHS_PER_LEVEL,
            "bus_factor_threshold": services.BUS_FACTOR_THRESHOLD,
        },
    )