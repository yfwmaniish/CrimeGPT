"""DRF views for the core API."""
import io

from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .documents import (
    build_court_custody_context_from_case,
    build_medical_context_from_case,
    build_remand_context_from_case,
    build_seizure_context_from_case,
    render_court_custody_letter,
    render_medical_treatment_letter,
    render_remand_request,
    render_seizure_receipt,
)
from .models import Case, CaseSection, DiaryEvent, Document, LegalSection
from .serializers import CaseSerializer


def _user_payload(user):
    return {
        "username": user.username,
        "role": user.role,
        "role_display": user.get_role_display(),
        "can_generate_documents": user.role in ("IO", "SHO"),
    }


class LoginView(APIView):
    """Exchange username/password for a token (used by the React SPA)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(
            request,
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, **_user_payload(user)})


class MeView(APIView):
    """Return the current user (lets the SPA restore session from a stored token)."""

    def get(self, request):
        return Response(_user_payload(request.user))


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

    def _finalize_document(self, request, case, *, doc_type, label, filename_prefix, rendered):
        """Shared generation tail: version (never overwrite), save the Document,
        log a DiaryEvent, return the standard response. Used by every document
        endpoint so versioning + audit logic lives in one place.
        """
        buffer = io.BytesIO()
        rendered.save(buffer)

        last_version = (
            Document.objects.filter(case=case, doc_type=doc_type).aggregate(
                m=Max("version")
            )["m"]
            or 0
        )
        version = last_version + 1

        with transaction.atomic():
            document = Document(case=case, doc_type=doc_type, version=version)
            document.file.save(
                f"{filename_prefix}_case{case.id}_v{version}.docx",
                ContentFile(buffer.getvalue()),
                save=False,
            )
            document.save()

            event = DiaryEvent.objects.create(
                case=case,
                timestamp=timezone.now(),
                event_type="DOCUMENT_GENERATED",
                description=f"{label} (version {version}) generated.",
                actor=request.user,
            )

        return Response(
            {
                "id": document.id,
                "doc_type": document.doc_type,
                "version": document.version,
                "download_url": request.build_absolute_uri(document.file.url),
                "generated_at": document.generated_at,
                "diary_event": {
                    "id": event.id,
                    "event_type": event.event_type,
                    "description": event.description,
                    "timestamp": event.timestamp,
                    "actor": event.actor.username if event.actor else None,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="documents/seizure",
        url_name="generate-seizure",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def generate_seizure(self, request, pk=None):
        """Generate (or regenerate, versioned) the Seizure Receipt for this case."""
        case = self.get_object()
        rendered = render_seizure_receipt(build_seizure_context_from_case(case))
        return self._finalize_document(
            request, case,
            doc_type="SEIZURE", label="Seizure Receipt",
            filename_prefix="seizure_receipt", rendered=rendered,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="documents/remand",
        url_name="generate-remand",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def generate_remand(self, request, pk=None):
        """Generate (or regenerate, versioned) the Police-Custody Remand Request.

        Pulls only CONFIRMED sections and the latest ARREST diary event.
        """
        case = self.get_object()
        rendered = render_remand_request(build_remand_context_from_case(case))
        return self._finalize_document(
            request, case,
            doc_type="REMAND", label="Remand Request",
            filename_prefix="remand_request", rendered=rendered,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="documents/custody",
        url_name="generate-custody",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def generate_custody(self, request, pk=None):
        """Generate (or regenerate, versioned) the Court (Judicial) Custody Letter.

        Pulls only CONFIRMED sections.
        """
        case = self.get_object()
        rendered = render_court_custody_letter(build_court_custody_context_from_case(case))
        return self._finalize_document(
            request, case,
            doc_type="CUSTODY", label="Court Custody Letter",
            filename_prefix="court_custody_letter", rendered=rendered,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="documents/medical",
        url_name="generate-medical",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def generate_medical(self, request, pk=None):
        """Generate (or regenerate, versioned) the Medical Treatment Letter.

        Subject is the VICTIM, falling back to the ACCUSED, else blank.
        """
        case = self.get_object()
        rendered = render_medical_treatment_letter(build_medical_context_from_case(case))
        return self._finalize_document(
            request, case,
            doc_type="MEDICAL", label="Medical Treatment Letter",
            filename_prefix="medical_treatment_letter", rendered=rendered,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="suggest-sections",
        url_name="suggest-sections",
        permission_classes=[IsAuthenticated],
    )
    def suggest_sections(self, request, pk=None):
        """Suggest BNS sections for this case by semantic similarity to its
        incident_narrative.

        Embeds the narrative, runs a pgvector cosine search over LegalSection,
        and records the top N as CaseSection rows with suggested_by_ai=True,
        confirmed=False. AI suggests; the officer confirms separately. Existing
        rows (including ones already confirmed) are never modified, so re-running
        never duplicates or auto-confirms anything.
        """
        from pgvector.django import CosineDistance

        from .embeddings import embed_text

        case = self.get_object()
        narrative = (case.incident_narrative or "").strip()
        if not narrative:
            return Response(
                {"detail": "This case has no incident_narrative to analyse."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            top_n = int(request.query_params.get("n", 5))
        except (TypeError, ValueError):
            top_n = 5
        top_n = max(1, min(top_n, 50))

        query_vector = embed_text(narrative)
        candidates = (
            LegalSection.objects.filter(embedding__isnull=False)
            .annotate(distance=CosineDistance("embedding", query_vector))
            .order_by("distance")[:top_n]
        )

        results = []
        with transaction.atomic():
            for section in candidates:
                # get_or_create never touches an existing row, so a previously
                # confirmed suggestion stays confirmed and is not duplicated.
                case_section, _ = CaseSection.objects.get_or_create(
                    case=case,
                    section=section,
                    defaults={"suggested_by_ai": True, "confirmed": False},
                )
                results.append(
                    {
                        "case_section_id": case_section.id,
                        "section_id": section.id,
                        "code": section.code,
                        "section_number": section.section_number,
                        "title": section.title,
                        "ipc_equivalent": section.ipc_equivalent,
                        "similarity": round(1.0 - float(section.distance), 4),
                        "suggested_by_ai": case_section.suggested_by_ai,
                        "confirmed": case_section.confirmed,
                    }
                )

        return Response({"count": len(results), "results": results})
