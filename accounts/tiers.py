from functools import wraps

from django.core.exceptions import PermissionDenied

from teams.models import TeamMembership


def require_tier(*tiers):
    def decorator(view):
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.tier not in tiers:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return _wrapped

    return decorator


def manages_team(user, team):
    return TeamMembership.objects.filter(
        team=team,
        user=user,
        role=TeamMembership.Role.MANAGER,
    ).exists()


def managed_team_ids(user):
    return TeamMembership.objects.filter(
        user=user,
        role=TeamMembership.Role.MANAGER,
    ).values_list("team_id", flat=True)


def team_member_ids(user):
    return TeamMembership.objects.filter(
        team_id__in=managed_team_ids(user),
    ).values_list("user_id", flat=True)