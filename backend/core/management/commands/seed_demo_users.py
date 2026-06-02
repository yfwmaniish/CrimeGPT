"""Create demo accounts so a fresh clone can try the UI flow immediately.

    python manage.py seed_demo_users

Creates (idempotent; resets passwords each run):
    io    / io12345    (Investigating Officer)   - can generate documents
    sho   / sho12345   (Station House Officer)    - can generate documents
    legal / legal12345 (Legal Advisor)            - cannot generate (for the 403 demo)

These are throwaway local-dev credentials. Do not use them anywhere real.
"""
from django.core.management.base import BaseCommand

from core.models import User

DEMO_USERS = [
    ("io", "io12345", "IO"),
    ("sho", "sho12345", "SHO"),
    ("legal", "legal12345", "LEGAL"),
]


class Command(BaseCommand):
    help = "Create/refresh demo IO/SHO/LEGAL accounts for the UI walkthrough."

    def handle(self, *args, **options):
        for username, password, role in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "police_station": "PS-Central"},
            )
            user.role = role
            user.police_station = user.police_station or "PS-Central"
            user.set_password(password)
            user.save()
            verb = "created" if created else "updated"
            self.stdout.write(f"  {verb}: {username} / {password}  ({role})")
        self.stdout.write(self.style.SUCCESS("Demo users ready."))
