from django.test import TestCase
from rest_framework.test import APIClient

from .models import Organization, User


class AccountApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test Labs", slug="test-labs")
        self.user = User.objects.create_user(
            username="analyst",
            password="TestingPass123!",
            organization=self.organization,
            role=User.ROLE_ANALYST,
        )
        self.client = APIClient()

    def test_token_authentication(self):
        response = self.client.post("/api/accounts/token/", {"username": "analyst", "password": "TestingPass123!"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        me = self.client.get("/api/accounts/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["username"], "analyst")

    def test_role_defaults_to_viewer(self):
        self.assertEqual(User.ROLE_VIEWER, "viewer")
        self.assertTrue(self.user.is_analyst_role)
