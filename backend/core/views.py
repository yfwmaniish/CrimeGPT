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
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import (
    SAFE_METHODS,
    AllowAny,
    BasePermission,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .documents import (
    SUPPORTED_LANGS,
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
from .models import (
    Case,
    CaseJudgment,
    CaseSection,
    DiaryEvent,
    Document,
    EvidenceImage,
    LandmarkJudgment,
    LegalSection,
    Party,
)
from .pdf import convert_docx_to_pdf
from .serializers import (
    CaseSerializer,
    DiaryEventSerializer,
    EvidenceImageSerializer,
    validate_image_file,
)


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
    # Keyword/case-number search (?search=). Applied AFTER get_queryset scoping,
    # so an officer never finds another officer's case via search.
    filter_backends = [SearchFilter]
    search_fields = ["case_number", "fir_number", "incident_narrative", "police_station"]

    def get_queryset(self):
        qs = super().get_queryset()
        # "My Cases": the list is scoped to the cases the officer owns. Detail and
        # all other actions stay on the full set (so, e.g., an SHO can act on, and
        # a Legal Advisor can view the diary of, a case another officer created).
        if self.action == "list":
            qs = qs.filter(io=self.request.user)
        return qs

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
        """Generate (or regenerate, versioned) the Seizure Receipt for this case.

        ``?lang=en|hi|gu`` selects the translated template (default en). Only the
        Seizure Receipt is multilingual so far; the other documents ignore lang.
        """
        lang = request.query_params.get("lang", "en")
        if lang not in SUPPORTED_LANGS:
            lang = "en"
        case = self.get_object()
        rendered = render_seizure_receipt(build_seizure_context_from_case(case), lang=lang)
        return self._finalize_document(
            request, case,
            doc_type="SEIZURE", label="Seizure Receipt",
            filename_prefix=f"seizure_receipt_{lang}", rendered=rendered,
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

        Pulls only CONFIRMED sections and the arrest details. ``?custody_days=N``
        is a one-time input for the requested custody period (blank if omitted).
        """
        case = self.get_object()
        try:
            custody_days = int(request.query_params.get("custody_days", ""))
            if custody_days <= 0 or custody_days > 90:
                custody_days = None
        except (TypeError, ValueError):
            custody_days = None
        rendered = render_remand_request(
            build_remand_context_from_case(case, custody_days=custody_days)
        )
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

    @action(
        detail=True,
        methods=["post"],
        url_path=r"sections/(?P<cs_id>[^/.]+)/confirm",
        url_name="confirm-section",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def confirm_section(self, request, pk=None, cs_id=None):
        """Confirm (or un-confirm) a suggested section for this case — the
        officer's explicit decision. Body: ``{"confirmed": true|false}``
        (defaults to true). Only confirmed sections ever reach a document.
        """
        case = self.get_object()
        try:
            case_section = case.applied_sections.select_related("section").get(id=cs_id)
        except CaseSection.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        case_section.confirmed = bool(request.data.get("confirmed", True))
        case_section.save(update_fields=["confirmed"])
        return Response(
            {
                "case_section_id": case_section.id,
                "section_number": case_section.section.section_number,
                "title": case_section.section.title,
                "confirmed": case_section.confirmed,
            }
        )

    # ------------------------------------------------------------------ #
    # Landmark judgments / case laws
    # ------------------------------------------------------------------ #
    @staticmethod
    def _judgment_dict(judgment, applied, similarity=None):
        data = {
            "id": judgment.id,
            "title": judgment.title,
            "citation": judgment.citation,
            "year": judgment.year,
            "court": judgment.court,
            "principle": judgment.principle,
            "summary": judgment.summary,
            "applied": applied,
        }
        if similarity is not None:
            data["similarity"] = similarity
        return data

    @action(detail=True, methods=["get"], url_path="judgments", url_name="judgments")
    def judgments(self, request, pk=None):
        """Judgments relevant to this case's CONFIRMED sections, each with whether
        the officer has applied it. Read-only; any authenticated user."""
        case = self.get_object()
        confirmed_section_ids = case.applied_sections.filter(confirmed=True).values_list(
            "section_id", flat=True
        )
        applied_map = {cj.judgment_id: cj.applied for cj in case.case_judgments.all()}
        judgments = (
            LandmarkJudgment.objects.filter(sections__in=confirmed_section_ids)
            .distinct()
            .order_by("title")
        )
        results = [self._judgment_dict(j, applied_map.get(j.id, False)) for j in judgments]
        return Response({"count": len(results), "results": results})

    @action(
        detail=True,
        methods=["post"],
        url_path="suggest-judgments",
        url_name="suggest-judgments",
        permission_classes=[IsAuthenticated],
    )
    def suggest_judgments(self, request, pk=None):
        """Suggest landmark judgments by similarity to the incident narrative.
        Records each as a CaseJudgment (suggested_by_ai=True, applied=False);
        AI suggests, the officer applies. Returns citation + one-line principle."""
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
        top_n = max(1, min(top_n, 25))

        query_vector = embed_text(narrative)
        candidates = (
            LandmarkJudgment.objects.filter(embedding__isnull=False)
            .annotate(distance=CosineDistance("embedding", query_vector))
            .order_by("distance")[:top_n]
        )
        results = []
        with transaction.atomic():
            for judgment in candidates:
                case_judgment, _ = CaseJudgment.objects.get_or_create(
                    case=case,
                    judgment=judgment,
                    defaults={"suggested_by_ai": True, "applied": False},
                )
                results.append(
                    self._judgment_dict(
                        judgment,
                        case_judgment.applied,
                        similarity=round(1.0 - float(judgment.distance), 4),
                    )
                )
        return Response({"count": len(results), "results": results})

    @action(
        detail=True,
        methods=["post"],
        url_path=r"judgments/(?P<judgment_id>[^/.]+)/apply",
        url_name="apply-judgment",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
    )
    def apply_judgment(self, request, pk=None, judgment_id=None):
        """Mark a judgment as applied (or not) to this case — the officer's
        explicit decision. Body: ``{"applied": true|false}`` (defaults true).
        Only applied judgments reach documents."""
        case = self.get_object()
        try:
            judgment = LandmarkJudgment.objects.get(id=judgment_id)
        except LandmarkJudgment.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        case_judgment, _ = CaseJudgment.objects.get_or_create(case=case, judgment=judgment)
        case_judgment.applied = bool(request.data.get("applied", True))
        case_judgment.save(update_fields=["applied"])
        return Response(self._judgment_dict(judgment, case_judgment.applied))

    @action(
        detail=True,
        methods=["post"],
        url_path=r"parties/(?P<party_id>[^/.]+)/photo",
        url_name="party-photo",
        permission_classes=[IsAuthenticated, CanGenerateDocuments],
        parser_classes=[MultiPartParser, FormParser],
    )
    def party_photo(self, request, pk=None, party_id=None):
        """Upload a photo for a party (used by the Face Identification Form).
        Multipart field name: ``photo``. IO/SHO only."""
        case = self.get_object()
        try:
            party = case.parties.get(id=party_id)
        except Party.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        upload = request.FILES.get("photo")
        if not upload:
            return Response({"detail": "No photo file provided."}, status=status.HTTP_400_BAD_REQUEST)
        validate_image_file(upload)  # raises 400 on bad size/format
        party.photo = upload
        party.save(update_fields=["photo"])
        return Response({"id": party.id, "photo": request.build_absolute_uri(party.photo.url)})


class CanManageEvidence(BasePermission):
    """Any authenticated user may view evidence; only IO/SHO may add or delete."""

    message = "Only Investigating Officers (IO) and Station House Officers (SHO) may add or remove evidence."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(user, "role", "") in ("IO", "SHO")


class EvidenceImageViewSet(viewsets.ModelViewSet):
    """CRUD for evidence images. Filter the list with ?case=<id> and ?tag=<tag>.
    Adding an image auto-logs an EVIDENCE_UPLOADED diary event."""

    serializer_class = EvidenceImageSerializer
    permission_classes = [CanManageEvidence]
    parser_classes = [MultiPartParser, FormParser]
    queryset = EvidenceImage.objects.select_related("uploaded_by", "case").all()

    def get_queryset(self):
        qs = super().get_queryset()
        case_id = self.request.query_params.get("case")
        if case_id:
            qs = qs.filter(case_id=case_id)
        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__icontains=tag.strip())
        return qs

    def perform_create(self, serializer):
        evidence = serializer.save(uploaded_by=self.request.user)
        caption = evidence.description or "image"
        tags = f" [{evidence.tags}]" if evidence.tags else ""
        DiaryEvent.objects.create(
            case=evidence.case,
            timestamp=timezone.now(),
            event_type="EVIDENCE_UPLOADED",
            description=f"Evidence uploaded: {caption}{tags}",
            actor=self.request.user,
        )
