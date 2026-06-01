"""DRF views for the core API."""
import io

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .documents import build_seizure_context_from_case, render_seizure_receipt
from .models import Case, DiaryEvent, Document
from .serializers import CaseSerializer


class CanGenerateDocuments(BasePermission):
    """Only Investigating Officers (IO) and Station House Officers (SHO) may
    generate case documents."""

    message = "Only Investigating Officers (IO) and Station House Officers (SHO) may generate documents."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", "") in ("IO", "SHO")
        )


class CaseViewSet(viewsets.ModelViewSet):
    """Full CRUD for Case, including nested parties/seized items/statements.

    See CaseSerializer for the nested write contract.
    """

    serializer_class = CaseSerializer
    queryset = (
        Case.objects.select_related("io")
        .prefetch_related("parties", "seized_items", "statements")
        .all()
    )

    @action(
        detail=True,
        methods=["post"],
        url_path="documents/seizure",
        url_name="generate-seizure",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def generate_seizure(self, request, pk=None):
        """Generate (or regenerate, with an incremented version) the Seizure
        Receipt for this case, log a diary event, and return a download URL."""
        case = self.get_object()

        # Render the document from case data.
        context = build_seizure_context_from_case(case)
        rendered = render_seizure_receipt(context)
        buffer = io.BytesIO()
        rendered.save(buffer)

        # Never overwrite an existing receipt — bump the version instead.
        last_version = (
            Document.objects.filter(case=case, doc_type="SEIZURE").aggregate(
                m=Max("version")
            )["m"]
            or 0
        )
        version = last_version + 1

        with transaction.atomic():
            document = Document(case=case, doc_type="SEIZURE", version=version)
            document.file.save(
                f"seizure_receipt_case{case.id}_v{version}.docx",
                ContentFile(buffer.getvalue()),
                save=False,
            )
            document.save()

            DiaryEvent.objects.create(
                case=case,
                timestamp=timezone.now(),
                event_type="DOCUMENT_GENERATED",
                description=f"Seizure Receipt (version {version}) generated.",
                actor=request.user,
            )

        return Response(
            {
                "id": document.id,
                "doc_type": document.doc_type,
                "version": document.version,
                "download_url": request.build_absolute_uri(document.file.url),
                "generated_at": document.generated_at,
            },
            status=status.HTTP_201_CREATED,
        )
