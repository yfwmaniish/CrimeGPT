"""
DRF serializers for the Case spine, with nested write support.

A single POST to ``/api/cases/`` creates the Case together with its parties,
seized items and statements. DRF does not do nested writes out of the box, so
``CaseSerializer.create()`` / ``update()`` are overridden.

Referencing parties that don't have ids yet
-------------------------------------------
A seized item's ``seized_from`` and a statement's ``party`` are foreign keys to a
Party that may be created in the *same* request. Since those parties have no ids
yet, the client references them by **position** in the request's ``parties``
list:

    "seized_items": [{"description": "...", "seized_from_index": 1}]
    "statements":   [{"text": "...", "party_index": 0}]

On read, ``seized_from`` and ``party`` are returned as plain ids.

Update semantics
----------------
A nested collection is only touched if its key is present in the request
(``None`` => absent => left as-is). When present it is **replaced** (delete +
recreate), so editing the whole case is a single predictable PUT. Because
replacing ``parties`` cascades to its dependents, send ``parties``,
``seized_items`` and ``statements`` together when you change parties.
"""
from django.db import transaction
from PIL import Image
from rest_framework import serializers

from .models import Case, DiaryEvent, EvidenceImage, Party, SeizedItem, Statement, User

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "GIF", "WEBP", "BMP"}


def validate_image_file(f):
    """Reject non-images, oversized files, and uncommon formats (Pillow)."""
    if f.size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError("Image must be 5 MB or smaller.")
    try:
        img = Image.open(f)
        fmt = (img.format or "").upper()
        img.verify()  # checks the file is a valid, non-corrupt image
    except serializers.ValidationError:
        raise
    except Exception:
        raise serializers.ValidationError("File is not a valid image.")
    finally:
        f.seek(0)
    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise serializers.ValidationError(
            f"Unsupported image format ({fmt or 'unknown'}). Use JPEG, PNG, GIF, WEBP or BMP."
        )
    return f


class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = [
            "id",
            "role",
            "name",
            "parent_name",
            "age",
            "gender",
            "address",
            "phone",
            "id_type",
            "id_number",
        ]


class SeizedItemSerializer(serializers.ModelSerializer):
    # Write-only: 0-based index into this request's `parties` (usually accused).
    seized_from_index = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="0-based index into the case's `parties` list.",
    )
    # Read-only: the resolved party id.
    seized_from = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SeizedItem
        fields = [
            "id",
            "description",
            "quantity",
            "seized_from",
            "seized_from_index",
            "seizure_date",
            "seizure_place",
        ]


class StatementSerializer(serializers.ModelSerializer):
    party_index = serializers.IntegerField(
        write_only=True,
        required=False,
        help_text="0-based index into the case's `parties` list (the deponent).",
    )
    party = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Statement
        fields = ["id", "party", "party_index", "text", "recorded_date"]


class CaseSerializer(serializers.ModelSerializer):
    parties = PartySerializer(many=True, required=False)
    seized_items = SeizedItemSerializer(many=True, required=False)
    statements = StatementSerializer(many=True, required=False)
    # Defaults to the requesting user when omitted (see create()).
    io = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    io_username = serializers.CharField(source="io.username", read_only=True)

    class Meta:
        model = Case
        fields = [
            "id",
            "case_number",
            "fir_number",
            "fir_date",
            "police_station",
            "status",
            "incident_date",
            "incident_place",
            "incident_narrative",
            "io",
            "io_username",
            "created_at",
            "parties",
            "seized_items",
            "statements",
        ]
        read_only_fields = ["created_at"]

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_party(party_list, index, field):
        """Map a submitted index onto a created/existing Party, or None."""
        if index is None:
            return None
        if index < 0 or index >= len(party_list):
            raise serializers.ValidationError(
                {field: f"index {index} is out of range for {len(party_list)} parties."}
            )
        return party_list[index]

    def _sync_nested(self, case, parties_data, items_data, statements_data):
        """Create/replace the nested collections. ``None`` => leave untouched."""
        if parties_data is not None:
            case.parties.all().delete()
            for party_data in parties_data:
                Party.objects.create(case=case, **party_data)

        # Insertion order == submission order; index references rely on this.
        party_list = list(case.parties.order_by("id"))

        if items_data is not None:
            case.seized_items.all().delete()
            for item_data in items_data:
                index = item_data.pop("seized_from_index", None)
                seized_from = self._resolve_party(party_list, index, "seized_from_index")
                SeizedItem.objects.create(case=case, seized_from=seized_from, **item_data)

        if statements_data is not None:
            case.statements.all().delete()
            for statement_data in statements_data:
                index = statement_data.pop("party_index", None)
                if index is None:
                    raise serializers.ValidationError(
                        {"statements": "Each statement requires a party_index."}
                    )
                party = self._resolve_party(party_list, index, "party_index")
                Statement.objects.create(case=case, party=party, **statement_data)

    # ------------------------------------------------------------------ #
    # create / update
    # ------------------------------------------------------------------ #
    @transaction.atomic
    def create(self, validated_data):
        parties_data = validated_data.pop("parties", [])
        items_data = validated_data.pop("seized_items", [])
        statements_data = validated_data.pop("statements", [])

        if "io" not in validated_data:
            request = self.context.get("request")
            if request and request.user and request.user.is_authenticated:
                validated_data["io"] = request.user
            else:
                raise serializers.ValidationError({"io": "This field is required."})

        case = Case.objects.create(**validated_data)
        self._sync_nested(case, parties_data, items_data, statements_data)
        return case

    @transaction.atomic
    def update(self, instance, validated_data):
        # None => key absent => leave that collection untouched.
        parties_data = validated_data.pop("parties", None)
        items_data = validated_data.pop("seized_items", None)
        statements_data = validated_data.pop("statements", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        self._sync_nested(instance, parties_data, items_data, statements_data)
        return instance


class DiaryEventSerializer(serializers.ModelSerializer):
    """Read/write serializer for case diary events.

    On read, ``actor`` is the username. On write (manual entry), ``description``
    is required; ``event_type`` defaults to MANUAL and ``timestamp`` to now (set
    in the view). ``actor`` and ``case`` are set server-side, never from input.
    """

    actor = serializers.SerializerMethodField()
    event_type = serializers.CharField(required=False, default="MANUAL", max_length=50)
    timestamp = serializers.DateTimeField(required=False)

    class Meta:
        model = DiaryEvent
        fields = ["id", "timestamp", "event_type", "description", "actor"]

    def get_actor(self, obj):
        return obj.actor.username if obj.actor else None


class EvidenceImageSerializer(serializers.ModelSerializer):
    """Evidence image with caption + comma-separated tags. uploaded_by/at are
    set server-side; the image is validated for size and format."""

    uploaded_by = serializers.SerializerMethodField()
    tag_list = serializers.SerializerMethodField()

    class Meta:
        model = EvidenceImage
        fields = ["id", "case", "image", "description", "tags", "tag_list", "uploaded_by", "uploaded_at"]
        read_only_fields = ["uploaded_at"]

    def get_uploaded_by(self, obj):
        return obj.uploaded_by.username if obj.uploaded_by else None

    def get_tag_list(self, obj):
        return obj.tag_list()

    def validate_image(self, value):
        return validate_image_file(value)
