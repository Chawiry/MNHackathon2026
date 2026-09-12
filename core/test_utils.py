from accounts.models import Tier, User
from teams.models import Team, TeamMembership


def make_user(username, tier=Tier.EMPLOYEE, password="testpass123"):
    return User.objects.create_user(username=username, password=password, tier=tier)


def make_team(name, manager=None, members=()):
    team = Team.objects.create(name=name)
    if manager is not None:
        TeamMembership.objects.create(
            team=team, user=manager, role=TeamMembership.Role.MANAGER
        )
    for member in members:
        TeamMembership.objects.create(
            team=team, user=member, role=TeamMembership.Role.MEMBER
        )
    return team