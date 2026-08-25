import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_full_auth_org_and_infra_flow() -> None:
    """Integration test verifying Phase 2 (Auth/Orgs) and Phase 3 (Infrastructure) endpoints."""
    uid = uuid.uuid4().hex[:6]
    admin_email = f"admin_{uid}@pantheon-cyber.io"
    tester_email = f"tester_{uid}@pantheon-cyber.io"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Register User & Org
        reg_payload = {
            "email": admin_email,
            "password": "Password123!",
            "full_name": "Cyber Admin",
            "org_name": f"Pantheon Cyber {uid}",
        }
        res_reg = await client.post("/api/auth/register", json=reg_payload)
        assert res_reg.status_code == 201, res_reg.text
        token_data = res_reg.json()
        assert "access_token" in token_data
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Current User Profile (/api/auth/me)
        res_me = await client.get("/api/auth/me", headers=headers)
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["email"] == admin_email
        assert me_data["role"] == "admin"

        # 3. Get Current Org (/api/orgs/current)
        res_org = await client.get("/api/orgs/current", headers=headers)
        assert res_org.status_code == 200
        org_data = res_org.json()
        assert org_data["name"] == f"Pantheon Cyber {uid}"
        assert org_data["cluster_status"] in ["provisioning", "ready"]

        # 4. List Team Members (/api/orgs/members)
        res_members = await client.get("/api/orgs/members", headers=headers)
        assert res_members.status_code == 200
        members = res_members.json()
        assert len(members) >= 1
        assert members[0]["user_email"] == admin_email

        # 5. Invite Teammate (/api/orgs/invitations)
        invite_payload = {"email": tester_email, "role": "tester"}
        res_inv = await client.post("/api/orgs/invitations", json=invite_payload, headers=headers)
        assert res_inv.status_code == 201
        inv_data = res_inv.json()
        assert inv_data["email"] == tester_email
        invite_token = inv_data["token"]

        # 6. Accept Teammate Invitation (/api/orgs/invitations/accept)
        accept_payload = {
            "token": invite_token,
            "password": "Password456!",
            "full_name": "Security Tester",
        }
        res_acc = await client.post("/api/orgs/invitations/accept", json=accept_payload)
        assert res_acc.status_code == 200
        assert "access_token" in res_acc.json()

        # 7. Check Audit Log (/api/audit-log)
        res_audit = await client.get("/api/orgs/audit-log", headers=headers)
        assert res_audit.status_code == 200
        audit_entries = res_audit.json()
        assert len(audit_entries) >= 2
        actions = [entry["action"] for entry in audit_entries]
        assert "user.register" in actions
        assert "org.invite" in actions

        # 8. Check Infrastructure View (/api/infrastructure/resources) — Phase 3
        res_infra = await client.get("/api/infrastructure/resources", headers=headers)
        assert res_infra.status_code == 200, res_infra.text
        infra_data = res_infra.json()
        assert "namespace" in infra_data
        assert infra_data["namespace"].startswith("pantheon-tenant-")
        assert "quota" in infra_data
        assert len(infra_data["network_policies"]) >= 1
        assert infra_data["network_policies"][0]["name"] == "pantheon-default-deny"
