# GDPR Phase 2 Invitation Token Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove raw organization invitation tokens from the brokered notification path while preserving invitation delivery to the end recipient.

**Architecture:** Replace the public-event dispatch in the organizations invite flow with a dedicated organizations domain port for invitation delivery. Implement that port with an organizations infrastructure adapter that composes the notifications bounded context and optional accept-URL formatting, and remove the now-dead invitation event polling/wiring path.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, structured JSON logging, notifications adapters, Redis/RabbitMQ messaging

---

### Task 1: Add an Organizations Invitation Notifier Port

**Files:**
- Create: `apps/organizations/domain/invitation_notification.py`
- Create: `apps/organizations/domain/ports/organization_invitation_notifier.py`
- Modify: `apps/organizations/application/invite_organization_member.py`

- [ ] **Step 1: Define the notification payload dataclass**

```python
@dataclass(frozen=True, slots=True)
class OrganizationInvitationNotification:
    invitation_id: UUID
    organization_id: UUID
    organization_name: str
    email: str
    expires_at: datetime
    token: str
```

- [ ] **Step 2: Define the organizations domain port**

```python
class OrganizationInvitationNotifier(Protocol):
    async def send_invitation(self, notification: OrganizationInvitationNotification) -> None:
        """Deliver an organization invitation to its recipient."""
```

- [ ] **Step 3: Inject the notifier into the use case**

```python
class InviteOrganizationMember:
    def __init__(..., invitations: OrganizationInvitationRepository, notifier: OrganizationInvitationNotifier) -> None:
        ...
        self._notifier = notifier
```

- [ ] **Step 4: Replace broker dispatch with direct notification**

```python
await self._notifier.send_invitation(
    OrganizationInvitationNotification(
        invitation_id=invitation.id,
        organization_id=invitation.organization_id,
        organization_name=organization.name,
        email=invitation.email,
        expires_at=invitation.expires_at,
        token=raw_token,
    )
)
```

### Task 2: Implement the Notifications Adapter

**Files:**
- Create: `apps/organizations/infrastructure/notifications/__init__.py`
- Create: `apps/organizations/infrastructure/notifications/organization_invitation_notifier.py`
- Modify: `shipster/platform/notifications/deps.py`
- Modify: `apps/organizations/interfaces/dependencies.py`

- [ ] **Step 1: Implement an infrastructure adapter**

```python
class NotificationSenderOrganizationInvitationNotifier(OrganizationInvitationNotifier):
    def __init__(self, sender: NotificationSender, *, accept_url_template: str | None = None) -> None:
        ...
```

- [ ] **Step 2: Format the delivered message inside the adapter**

```python
accept_url = self._build_accept_url(notification)
text_body = (
    f"You have been invited to join {notification.organization_name}. "
    f"Use this link: {accept_url}. "
    f"Expires at: {notification.expires_at.isoformat()}."
)
```

- [ ] **Step 3: Wire the adapter from `shipster.platform.notifications.deps`**

Run: create `ensure_organization_invitation_notifier()` and async getter
Expected: transport wiring depends on platform settings, app logic depends only on the organizations port

- [ ] **Step 4: Inject the notifier from the organizations FastAPI dependency**

```python
async def get_invite_organization_member(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    notifier: OrganizationInvitationNotifier = Depends(get_organization_invitation_notifier),
) -> InviteOrganizationMember:
```

### Task 3: Remove the Dead Brokered Invitation Path

**Files:**
- Delete: `apps/organizations/domain/organization_public_events.py`
- Delete: `apps/organizations/domain/ports/organization_invitation_created_handler.py`
- Delete: `apps/organizations/application/messaging/organization_invitation_created_handler.py`
- Delete: `apps/organizations/application/messaging/process_organization_invitation_created_events.py`
- Delete: `apps/organizations/interfaces/invitation_created_poll.py`
- Delete: `apps/organizations/interfaces/schedule_job_ids.py`
- Modify: `apps/organizations/application/messaging/__init__.py`
- Modify: `apps/organizations/interfaces/schedule_registration.py`
- Modify: `shipster/platform/messaging/deps.py`
- Modify: `shipster/platform/messaging/__init__.py`

- [ ] **Step 1: Remove the organization public-event types and handlers**

Run: delete the invitation-created payload and handler protocol/modules
Expected: no organization invitation token is marshalled into broker envelopes

- [ ] **Step 2: Remove scheduler registration for invitation polling**

```python
def register(registry: ScheduleRegistry) -> None:
    del registry
```

- [ ] **Step 3: Remove no-longer-used platform messaging wiring**

Run: drop invitation-created handler wiring and the public event dispatcher getter/export if no callers remain
Expected: `shipster.platform.messaging` only exposes still-used generic messaging dependencies

### Task 4: Verify the Slice

**Files:**
- Verify: `apps/organizations/application/invite_organization_member.py`
- Verify: `apps/organizations/interfaces/dependencies.py`
- Verify: `apps/organizations/infrastructure/notifications/organization_invitation_notifier.py`
- Verify: `shipster/platform/notifications/deps.py`
- Verify: `shipster/platform/messaging/deps.py`

- [ ] **Step 1: Run Ruff format**

Run: `ruff format shipster apps`
Expected: files are formatted or already clean

- [ ] **Step 2: Run Ruff lint**

Run: `ruff check shipster apps`
Expected: exit 0

- [ ] **Step 3: Run syntax verification**

Run: `python3 -m compileall shipster apps`
Expected: exit 0

- [ ] **Step 4: Run import-linter**

Run: `.venv/bin/lint-imports`
Expected: exit 0
