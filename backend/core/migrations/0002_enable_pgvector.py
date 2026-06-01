"""Enable the pgvector extension.

Kept as a separate migration *after* 0001_initial so it is not the app's
first migration: the custom User model lives in 0001_initial, and Django's
swappable-user dependency resolves to the app's first migration. The schema
does not use a VectorField until Week 2 (legal retrieval); the extension is
installed now so the database is ready. Requires a Postgres image that ships
pgvector (see docker-compose: pgvector/pgvector).
"""
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        VectorExtension(),
    ]
