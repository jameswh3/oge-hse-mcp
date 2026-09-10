from __future__ import annotations

import json

from sqlalchemy import delete

from oge_hse_mcp.db import ensure_schema, session_scope
from oge_hse_mcp.models import Incident, Procedure


def _procedures() -> list[Procedure]:
    return [
        Procedure(id="HSE-GEN-001", title="Stop Work Authority", summary="How any worker can stop unsafe work.", content="Stop the task, make the area safe, notify the supervisor, and document the concern. Work resumes only after hazards and controls are reviewed.", category="safety", site_id=None, revision="3.1", effective_date="2026-01-15", owner="Fictitious HSE Governance"),
        Procedure(id="HSE-PTW-014", title="Hot Work Permit", summary="Permit and gas-testing controls for ignition-producing work.", content="Verify isolation, test the atmosphere, remove combustibles, assign a fire watch, and close the permit after the post-work watch period.", category="permit-to-work", site_id="DEMO-GULF", revision="2.4", effective_date="2026-02-01", owner="Fictitious Gulf Operations"),
        Procedure(id="HSE-LOTO-007", title="Electrical Lockout Tagout", summary="Isolation and zero-energy verification for electrical maintenance.", content="Identify energy sources, notify affected workers, isolate, lock and tag, release stored energy, and verify zero energy before work begins.", category="energy-isolation", site_id="DEMO-PERMIAN", revision="5.0", effective_date="2025-11-10", owner="Fictitious Permian Operations"),
    ]


def _incidents() -> list[Incident]:
    return [
        Incident(id="INC-2026-0042", title="Dropped hand tool near miss", description="A tethered wrench detached during elevated maintenance; the exclusion zone prevented exposure.", lesson_learned="Inspect tether anchor points and record pre-use checks in the work pack.", severity="near-miss", status="closed", site_id="DEMO-GULF", occurred_at="2026-03-12T14:25:00Z"),
        Incident(id="INC-2026-0061", title="Unexpected residual pressure", description="Residual pressure was found while opening a blinded line after the isolation check.", lesson_learned="Add a second bleed-point verification to the site isolation certificate.", severity="high-potential", status="actions-open", site_id="DEMO-PERMIAN", occurred_at="2026-05-08T09:10:00Z"),
    ]


def seed() -> dict[str, int]:
    ensure_schema()
    procedures = _procedures()
    incidents = _incidents()
    with session_scope() as session:
        session.execute(delete(Incident))
        session.execute(delete(Procedure))
        session.add_all(procedures)
        session.add_all(incidents)
    return {"procedures": len(procedures), "incidents": len(incidents)}


def main() -> None:
    print(json.dumps({"status": "ok", **seed()}, indent=2))


if __name__ == "__main__":
    main()
