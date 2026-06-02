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
from rest_framework.permissions import (
    SAFE_METHODS,
    AllowAny,
    BasePermission,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .documents import (
    build_chargesheet_context_from_case,
    build_court_custody_context_from_case,
    build_faceid_context_from_case,
    build_medical_context_from_case,
    build_panchanama_context_from_case,
    build_remand_context_from_case,
    build_seizure_context_from_case,
    render_chargesheet,
    render_court_custody_letter,
    render_faceid,
    render_medical_treatment_letter,
    render_panchanama,
    render_remand_request,
    render_seizure_receipt,
)
from .models import Case, CaseSection, DiaryEvent, Document, LegalSection
from .pdf import convert_docx_to_pdf
from .serializers import CaseSerializer, DiaryEventSerializer


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


class CanViewOrLogDiary(BasePermission):
    """Any authenticated user may read the diary; only IO/SHO may add events
    (same write RBAC as document generation)."""

    message = "Only Investigating Officers (IO) and Station House Officers (SHO) may add diary events."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(user, "role", "") in ("IO", "SHO")


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
        """Shared generation tail: version (never overwrite), save the Document
        (.docx, plus PDF when requested), log a DiaryEvent, return the standard
        response. Used by every document endpoint so versioning + audit + PDF
        logic lives in one place.

        Pass ``?format=pdf`` to also render a PDF (LibreOffice headless), store it
        on the Document, and make it the primary download.
        """
        buffer = io.BytesIO()
        rendered.save(buffer)
        docx_bytes = buffer.getvalue()

        want_pdf = request.query_params.get("format", "").lower() == "pdf"

        last_version = (
            Document.objects.filter(case=case, doc_type=doc_type).aggregate(
                m=Max("version")
            )["m"]
            or 0
        )
        version = last_version + 1
        base_name = f"{filename_prefix}_case{case.id}_v{version}"

        # Convert before opening the transaction (it shells out to LibreOffice).
        pdf_bytes = convert_docx_to_pdf(docx_bytes) if want_pdf else None

        with transaction.atomic():
            document = Document(case=case, doc_type=doc_type, version=version)
            document.file.save(f"{base_name}.docx", ContentFile(docx_bytes), save=False)
            if pdf_bytes is not None:
                document.pdf_file.save(f"{base_name}.pdf", ContentFile(pdf_bytes), save=False)
            document.save()

            event = DiaryEvent.objects.create(
                case=case,
                timestamp=timezone.now(),
                event_type="DOCUMENT_GENERATED",
                description=f"{label} (version {version}) generated.",
                actor=request.user,
            )

        docx_url = request.build_absolute_uri(document.file.url)
        pdf_url = request.build_absolute_uri(document.pdf_file.url) if document.pdf_file else None

        return Response(
            {
                "id": document.id,
                "doc_type": document.doc_type,
                "version": document.version,
                "docx_url": docx_url,
                "pdf_url": pdf_url,
                # Primary download follows the requested format.
                "download_url": pdf_url if want_pdf else docx_url,
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
        url_path="documents/chargesheet",
        url_name="generate-chargesheet",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def generate_chargesheet(self, request, pk=None):
        """Generate (or regenerate, versioned) the Purvani Chargesheet — the
        superset document (all parties, confirmed sections, seized items,
        statements, and a diary summary).
        """
        case = self.get_object()
        rendered = render_chargesheet(build_chargesheet_context_from_case(case))
        return self._finalize_document(
            request, case,
            doc_type="CHARGESHEET", label="Purvani Chargesheet",
            filename_prefix="purvani_chargesheet", rendered=rendered,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="documents/panchanama",
        url_name="generate-panchanama",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def generate_panchanama(self, request, pk=None):
        """Generate (or regenerate, versioned) the Accused Panchanama
        (accused + panch witnesses + seized articles)."""
        case = self.get_object()
        rendered = render_panchanama(build_panchanama_context_from_case(case))
        return self._finalize_document(
            request, case,
            doc_type="PANCHANAMA", label="Accused Panchanama",
            filename_prefix="accused_panchanama", rendered=rendered,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="documents/faceid",
        url_name="generate-faceid",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def generate_faceid(self, request, pk=None):
        """Generate (or regenerate, versioned) the Face Identification Form
        (accused particulars + a placeholder box for an affixed photograph)."""
        case = self.get_object()
        rendered = render_faceid(build_faceid_context_from_case(case))
        return self._finalize_document(
            request, case,
            doc_type="FACEID", label="Face Identification Form",
            filename_prefix="face_identification_form", rendered=rendered,
        )

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="diary",
        url_name="diary",
        permission_classes=[CanViewOrLogDiary],
    )
    def diary(self, request, pk=None):
        """Case diary timeline.

        GET: the case's events in chronological order (any authenticated user).
        POST: add a manual event (IO/SHO only) so investigative steps are
        recorded alongside the auto-logged system events.
        """
        case = self.get_object()

        if request.method == "POST":
            serializer = DiaryEventSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            timestamp = serializer.validated_data.get("timestamp") or timezone.now()
            event = serializer.save(case=case, actor=request.user, timestamp=timestamp)
            return Response(DiaryEventSerializer(event).data, status=status.HTTP_201_CREATED)

        events = case.diary.all().order_by("timestamp")
        return Response(DiaryEventSerializer(events, many=True).data)

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
