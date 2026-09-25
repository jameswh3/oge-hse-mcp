from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

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
    incidents = [
        Incident(id="INC-2026-0042", title="Dropped hand tool near miss", description="A tethered wrench detached during elevated maintenance; the exclusion zone prevented exposure.", lesson_learned="Inspect tether anchor points and record pre-use checks in the work pack.", severity="near-miss", status="closed", site_id="DEMO-GULF", occurred_at="2026-03-12T14:25:00Z"),
        Incident(id="INC-2026-0061", title="Unexpected residual pressure", description="Residual pressure was found while opening a blinded line after the isolation check.", lesson_learned="Add a second bleed-point verification to the site isolation certificate.", severity="high-potential", status="actions-open", site_id="DEMO-PERMIAN", occurred_at="2026-05-08T09:10:00Z"),
    ]
    scenarios = [
        ("Portable gas detector alarm", "A portable detector alarmed while the crew prepared to enter a confined space.", "Confirm calibration and complete atmospheric testing before entry."),
        ("Vehicle reversing near miss", "A light vehicle reversed toward a marked pedestrian route before the spotter intervened.", "Separate pedestrian routes and require a spotter in congested areas."),
        ("Handrail integrity issue", "A loose handrail was identified during a routine elevated-platform inspection.", "Include connection torque and corrosion checks in platform inspections."),
        ("Minor chemical splash", "A small chemical splash contacted protective clothing during container transfer.", "Verify hose connections and review chemical-resistant PPE before transfer."),
        ("Temporary power cable damage", "Inspection found abrasion on a temporary power cable near a walkway.", "Route temporary cables away from traffic and inspect them before each shift."),
        ("Lifting sling defect", "A pre-use check identified damaged stitching on a lifting sling.", "Quarantine defective lifting gear and document every pre-use inspection."),
        ("Scaffold access obstruction", "Stored materials partially obstructed the approved scaffold access point.", "Keep access routes clear and include housekeeping in scaffold inspections."),
        ("Unplanned equipment movement", "Stored energy caused equipment to shift slightly during maintenance preparation.", "Verify zero energy and secure movable components before maintenance."),
        ("Small hydraulic fluid release", "A worn fitting released a small amount of hydraulic fluid into secondary containment.", "Replace fittings at condition-based thresholds and verify containment readiness."),
        ("Heat stress symptoms", "A worker reported early heat stress symptoms during an outdoor inspection.", "Apply work-rest cycles and hydration checks based on current heat conditions."),
        ("Pinch-point exposure", "A hand approached a pinch point while a cover was being aligned.", "Use alignment tools and define hands-free positioning methods."),
        ("Falling-object potential", "An unsecured item was found near the edge of an elevated work area.", "Secure loose items and inspect dropped-object controls before work starts."),
        ("Permit scope mismatch", "The work party identified that the permit did not cover an added task.", "Stop work and revalidate the permit whenever the task scope changes."),
        ("Blocked emergency equipment", "Staged materials reduced access to emergency response equipment.", "Mark exclusion zones around emergency equipment and audit them each shift."),
        ("Noise protection gap", "A short-duration task began before hearing protection was available at the workface.", "Stage required PPE before authorizing work in designated noise zones."),
        ("Excavation edge concern", "Spoil placement was closer to an excavation edge than the site standard permits.", "Confirm spoil setbacks during excavation setup and daily inspections."),
        ("Line-of-fire exposure", "A worker briefly entered the potential travel path of a tensioned hose.", "Establish line-of-fire boundaries before pressurizing flexible connections."),
        ("Inadequate task lighting", "Lighting levels were insufficient for a night maintenance inspection.", "Measure task lighting and provide portable lighting before night work."),
    ]
    locations = [
        "compressor pad",
        "process deck",
        "maintenance workshop",
        "warehouse loading area",
        "tank battery",
        "utility corridor",
        "drilling support area",
        "administration yard",
    ]
    severities = ["near-miss", "low", "moderate", "high-potential"]
    statuses = ["closed", "actions-open", "under-review", "verified-complete"]
    start = datetime(2024, 1, 3, 8, 0, tzinfo=timezone.utc)
    for index in range(1, 199):
        title, description, lesson = scenarios[(index - 1) % len(scenarios)]
        location = locations[(index * 5) % len(locations)]
        occurred_at = start + timedelta(days=index * 4, hours=(index * 7) % 24, minutes=(index * 11) % 60)
        incidents.append(
            Incident(
                id=f"INC-SYN-{index:04d}",
                title=f"{title} at {location}",
                description=f"{description} This is synthetic training record {index:04d} from the {location}.",
                lesson_learned=lesson,
                severity=severities[(index - 1) % len(severities)],
                status=statuses[(index - 1) % len(statuses)],
                site_id="DEMO-GULF" if index % 2 else "DEMO-PERMIAN",
                occurred_at=occurred_at.isoformat().replace("+00:00", "Z"),
            )
        )
    return incidents


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
