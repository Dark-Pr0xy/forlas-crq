"""First-run bootstrap: owner account + demo scenarios mirroring the Alpha."""

from __future__ import annotations

import secrets

from sqlmodel import Session, select

from app.config import settings
from app.models._base import DecompositionMode, DistributionType, Role
from app.models.scenario import Scenario
from app.models.settings import AppSettings
from app.models.user import User
from app.security import hash_password
from app.services.ids import scenario_id


def _dist(t: DistributionType, **kwargs) -> dict:
    return {"type": t.value, **kwargs}


def _seed_scenarios() -> list[dict]:
    """The same six demo scenarios from the Alpha HTML, normalised to the
    persisted shape. Notes are dropped for brevity; the engine's defaults fill
    any unset distribution parameters at run time."""
    return [
        dict(
            name="Ransomware on production ERP",
            business_unit="Finance",
            owner_label="A. Singh",
            scenario_type="Ransomware",
            tags=["crown-jewel", "external"],
            tolerance=5_000_000,
            review_date="2026-05-12",
            assessment_date="2026-04-02",
            version_label="1.3",
            benchmark_group="Industry — Manufacturing",
            mode=DecompositionMode.TEF_VULN.value,
            inputs={
                "tef": _dist(DistributionType.PERT, min=1, mode=4, max=12),
                "vuln": _dist(DistributionType.PERT, min=0.05, mode=0.25, max=0.6),
                "plm": _dist(DistributionType.LOGNORMAL, min=200_000, max=6_000_000, mode=900_000),
                "slm": _dist(DistributionType.LOGNORMAL, min=100_000, max=8_000_000, mode=500_000),
                "slp_prob": _dist(DistributionType.PERT, min=0.3, mode=0.55, max=0.85),
            },
        ),
        dict(
            name="Insider data exfiltration — customer PII",
            business_unit="Customer Ops",
            owner_label="M. Walker",
            scenario_type="Insider",
            tags=["privacy", "regulated"],
            tolerance=2_500_000,
            review_date="2026-07-01",
            assessment_date="2026-03-20",
            version_label="1.0",
            benchmark_group="Cross-industry — Insider",
            mode=DecompositionMode.TEF_VULN.value,
            inputs={
                "tef": _dist(DistributionType.PERT, min=0.5, mode=1.5, max=4),
                "vuln": _dist(DistributionType.PERT, min=0.05, mode=0.25, max=0.6),
                "plm": _dist(DistributionType.LOGNORMAL, min=100_000, max=3_000_000, mode=600_000),
                "slm": _dist(DistributionType.PERT, min=25_000, mode=150_000, max=2_000_000),
                "slp_prob": _dist(DistributionType.PERT, min=0.1, mode=0.4, max=0.8),
            },
        ),
        dict(
            name="Web application breach (e-commerce)",
            business_unit="Digital",
            owner_label="J. Park",
            scenario_type="Web App Exploit",
            tags=["external", "pci"],
            tolerance=1_500_000,
            review_date="2026-06-15",
            assessment_date="2026-04-30",
            version_label="2.1",
            benchmark_group="Industry — Retail",
            mode=DecompositionMode.TEF_VULN.value,
            inputs={
                "tef": _dist(DistributionType.PERT, min=6, mode=18, max=48),
                "vuln": _dist(DistributionType.PERT, min=0.05, mode=0.25, max=0.6),
                "plm": _dist(DistributionType.LOGNORMAL, min=30_000, max=1_200_000, mode=180_000),
                "slm": _dist(DistributionType.LOGNORMAL, min=20_000, max=2_000_000, mode=120_000),
                "slp_prob": _dist(DistributionType.PERT, min=0.1, mode=0.4, max=0.8),
            },
        ),
        dict(
            name="Cloud misconfiguration — data exposure",
            business_unit="Engineering",
            owner_label="R. Okafor",
            scenario_type="Misconfiguration",
            tags=["cloud", "privacy"],
            tolerance=1_000_000,
            review_date="2026-08-05",
            assessment_date="2026-05-18",
            version_label="1.1",
            benchmark_group="Industry — Technology",
            mode=DecompositionMode.TEF_VULN.value,
            inputs={
                "tef": _dist(DistributionType.PERT, min=2, mode=8, max=20),
                "vuln": _dist(DistributionType.PERT, min=0.05, mode=0.25, max=0.6),
                "plm": _dist(DistributionType.LOGNORMAL, min=25_000, max=900_000, mode=150_000),
                "slm": _dist(DistributionType.PERT, min=25_000, mode=150_000, max=2_000_000),
                "slp_prob": _dist(DistributionType.PERT, min=0.2, mode=0.45, max=0.7),
            },
        ),
        dict(
            name="DDoS against customer portal",
            business_unit="Digital",
            owner_label="J. Park",
            scenario_type="Availability",
            tags=["external"],
            tolerance=600_000,
            review_date="2026-09-10",
            assessment_date="2026-05-05",
            version_label="1.0",
            benchmark_group="Industry — Retail",
            mode=DecompositionMode.TEF_VULN.value,
            inputs={
                "tef": _dist(DistributionType.PERT, min=4, mode=12, max=30),
                "vuln": _dist(DistributionType.PERT, min=0.05, mode=0.25, max=0.6),
                "plm": _dist(DistributionType.LOGNORMAL, min=10_000, max=400_000, mode=60_000),
                "slm": _dist(DistributionType.LOGNORMAL, min=5_000, max=300_000, mode=40_000),
                "slp_prob": _dist(DistributionType.PERT, min=0.1, mode=0.25, max=0.5),
            },
        ),
        dict(
            name="Supplier compromise — managed service provider",
            business_unit="IT",
            owner_label="L. Chen",
            scenario_type="Third Party",
            tags=["supply-chain"],
            tolerance=3_000_000,
            review_date="2026-06-22",
            assessment_date="2026-04-12",
            version_label="1.2",
            benchmark_group="Cross-industry — Third Party",
            mode=DecompositionMode.TEF_VULN.value,
            inputs={
                "tef": _dist(DistributionType.PERT, min=0.3, mode=1, max=3),
                "vuln": _dist(DistributionType.PERT, min=0.05, mode=0.25, max=0.6),
                "plm": _dist(DistributionType.LOGNORMAL, min=300_000, max=5_000_000, mode=1_200_000),
                "slm": _dist(DistributionType.LOGNORMAL, min=150_000, max=6_000_000, mode=800_000),
                "slp_prob": _dist(DistributionType.PERT, min=0.35, mode=0.6, max=0.85),
            },
        ),
    ]


def ensure_app_settings(db: Session) -> AppSettings:
    s = db.get(AppSettings, 1)
    if s is None:
        s = AppSettings(id=1, iterations=settings.default_iterations, seed=settings.default_seed)
        db.add(s)
        db.flush()
    return s


def ensure_bootstrap_owner(db: Session) -> tuple[User, str | None]:
    """Create the first-run owner account if no users exist. Returns the user
    plus the plaintext password if a random one was generated (to print once)."""
    existing = db.exec(select(User).limit(1)).first()
    if existing:
        return existing, None
    password = settings.bootstrap_owner_password or secrets.token_urlsafe(18)
    user = User(
        email=settings.bootstrap_owner_email,
        display_name=settings.bootstrap_owner_name,
        password_hash=hash_password(password),
        role=Role.OWNER,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user, (None if settings.bootstrap_owner_password else password)


def seed_demo_scenarios(db: Session, owner: User) -> int:
    if db.exec(select(Scenario).limit(1)).first():
        return 0
    inserted = 0
    for data in _seed_scenarios():
        scn = Scenario(
            public_id=scenario_id(),
            owner_user_id=owner.id,
            **data,
        )
        db.add(scn)
        inserted += 1
    db.flush()
    return inserted
