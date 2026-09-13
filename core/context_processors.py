from django.contrib.auth import get_user_model

from accounts.models import Tier
from accounts.tiers import team_member_ids
from skills.models import CertificateAward, SkillProficiency


def nav_context(request):
    """Extra auth-aware context for the shell (approval badges etc.)."""
    user = request.user
    if not user.is_authenticated:
        return {}
    if user.tier not in (Tier.TEAM_MANAGER, Tier.LEADERSHIP):
        return {}

    if user.tier == Tier.LEADERSHIP:
        member_ids = get_user_model().objects.values_list("id", flat=True)
    else:
        member_ids = team_member_ids(user)

    return {
        "pending_approval_count": (
            SkillProficiency.objects.filter(
                status=SkillProficiency.Status.PENDING, user_id__in=member_ids
            ).count()
            + CertificateAward.objects.filter(
                status=CertificateAward.Status.PENDING, user_id__in=member_ids
            ).count()
        )
    }