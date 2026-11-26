from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.permissions import IsAnalystOrAdmin
from apps.core.utils import request_organization

from .models import CaseEvidence, CaseNote, InvestigationCase
from .serializers import CaseEvidenceSerializer, CaseFromFindingsSerializer, CaseNoteSerializer, InvestigationCaseSerializer
from .services import create_case_from_findings


class InvestigationCaseViewSet(viewsets.ModelViewSet):
    queryset = InvestigationCase.objects.select_related("assigned_to", "created_by").prefetch_related("findings").all()
    serializer_class = InvestigationCaseSerializer
    permission_classes = [IsAnalystOrAdmin]
    filterset_fields = ["status", "priority", "assigned_to"]
    search_fields = ["case_id", "title", "description"]
    ordering_fields = ["opened_at", "updated_at", "priority"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset

    def perform_create(self, serializer):
        organization_id = request_organization(self.request)
        serializer.save(organization_id=organization_id, created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="from-findings")
    def create_from_findings(self, request):
        serializer = CaseFromFindingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=status.HTTP_400_BAD_REQUEST)
        values = serializer.validated_data
        assigned_to = values.get("assigned_to")
        assigned_user = User.objects.filter(id=assigned_to, organization_id=organization).first() if assigned_to else None
        if assigned_to and not assigned_user:
            return Response({"detail": "Assigned user must belong to this organization"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            case = create_case_from_findings(
                organization,
                values["finding_ids"],
                created_by=request.user,
                title=values.get("title"),
                description=values.get("description"),
                priority=values["priority"],
                assigned_to=assigned_user,
            )
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(case).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        case = self.get_object()
        case.assigned_to_id = request.data.get("assigned_to")
        case.status = request.data.get("status", "investigating")
        case.save(update_fields=["assigned_to", "status", "updated_at"])
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        case = self.get_object()
        notes = request.data.get("resolution_notes", "")
        if not notes:
            return Response({"detail": "resolution_notes is required"}, status=status.HTTP_400_BAD_REQUEST)
        case.status = request.data.get("status", "resolved")
        case.resolution_notes = notes
        case.closed_at = timezone.now()
        case.save(update_fields=["status", "resolution_notes", "closed_at", "updated_at"])
        return Response(self.get_serializer(case).data)


class CaseNoteViewSet(viewsets.ModelViewSet):
    queryset = CaseNote.objects.select_related("author", "case").all()
    serializer_class = CaseNoteSerializer
    permission_classes = [IsAnalystOrAdmin]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset

    def perform_create(self, serializer):
        organization_id = request_organization(self.request)
        serializer.save(organization_id=organization_id, author=self.request.user)


class CaseEvidenceViewSet(viewsets.ModelViewSet):
    queryset = CaseEvidence.objects.select_related("added_by", "case").all()
    serializer_class = CaseEvidenceSerializer
    permission_classes = [IsAnalystOrAdmin]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset

    def perform_create(self, serializer):
        organization_id = request_organization(self.request)
        serializer.save(organization_id=organization_id, added_by=self.request.user)
