"""Seed the deterministic demo organization (spec §3 / Gap 1).

Flushes the dev database, loads the base skills taxonomy, then builds the full
org: departments, projects, teams, employees, proficiencies, requirements,
the skills graph, certificates, future demand, criticality assessments, and
readiness trend snapshots.

Repeatable: running it again always produces the same dataset.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Flush the DB and seed the deterministic demo organization."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-flush",
            action="store_true",
            help="Skip the flush; assume the target tables are already empty.",
        )

    def handle(self, *args, **options):
        if not options["no_flush"]:
            self.stdout.write("Flushing database...")
            call_command("flush", interactive=False, verbosity=0)
        self.stdout.write("Loading base skills taxonomy (starter_skills)...")
        call_command("loaddata", "starter_skills", verbosity=0)

        from core.seed_data import run

        run(verbose=1)
        self.stdout.write(self.style.SUCCESS("seed_demo complete."))