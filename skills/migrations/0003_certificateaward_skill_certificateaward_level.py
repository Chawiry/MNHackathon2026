# Generated manually: add the skill/level that an approved certificate backs,
# so certificates can feed into proficiency/coverage analytics.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0002_certificateaward_approved_by_certificateaward_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="certificateaward",
            name="skill",
            field=models.ForeignKey(
                help_text="The skill this certificate confirms.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="certificate_awards",
                to="skills.skill",
            ),
        ),
        migrations.AddField(
            model_name="certificateaward",
            name="level",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Novice"),
                    (2, "Basic"),
                    (3, "Independent"),
                    (4, "Advanced"),
                    (5, "Expert"),
                ],
                help_text="Proficiency level this certificate confirms.",
            ),
        ),
    ]