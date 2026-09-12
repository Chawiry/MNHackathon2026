from django.db import migrations


def move_project_requirements(apps, schema_editor):
    ProjectSkillRequirement = apps.get_model("projects", "ProjectSkillRequirement")
    TeamSkillRequirement = apps.get_model("teams", "TeamSkillRequirement")
    for req in ProjectSkillRequirement.objects.select_related("project").iterator():
        team = req.project.teams.first()
        if team is None:
            continue
        TeamSkillRequirement.objects.create(
            team=team,
            skill_id=req.skill_id,
            required_level=req.required_level,
            importance=req.importance,
            people_needed=req.people_needed,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("teams", "0004_teamskillrequirement"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(move_project_requirements, migrations.RunPython.noop),
    ]