"""Hand-curated knowledge seed.

Substantive starter set covering the most-used items from each catalogue —
expandable by user imports. Source is "builtin" for the seed; user imports
land under their declared source name so the originals are recoverable.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.models.knowledge import BenchmarkEntry, ControlEntry, ThreatEntry

# ----------------------------------------------------------------- threats


THREATS: list[dict] = [
    # FAIR threat communities
    {
        "public_id": "fair-tc-cybercriminals",
        "name": "Cybercriminals",
        "category": "FAIR threat community",
        "description": "Financially motivated external actors — ransomware crews, fraud rings, data extortion groups. Generally opportunistic, increasingly capable.",
        "references": ["FAIR Institute — Threat Community Reference"],
    },
    {
        "public_id": "fair-tc-nation-state",
        "name": "Nation-state actors",
        "category": "FAIR threat community",
        "description": "State-sponsored actors targeting espionage, sabotage or pre-positioning. High capability, long dwell time, low frequency for most SMBs.",
        "references": ["FAIR Institute — Threat Community Reference"],
    },
    {
        "public_id": "fair-tc-hacktivists",
        "name": "Hacktivists",
        "category": "FAIR threat community",
        "description": "Ideologically motivated actors. Tactics include DDoS, defacement, doxing.",
    },
    {
        "public_id": "fair-tc-malicious-insider",
        "name": "Malicious insider",
        "category": "FAIR threat community",
        "description": "Trusted users acting with intent to harm — IP theft, fraud, sabotage.",
    },
    {
        "public_id": "fair-tc-careless-insider",
        "name": "Careless insider",
        "category": "FAIR threat community",
        "description": "Unintentional insider risk — misdirected emails, S3 misconfigurations, unsanctioned tools.",
    },
    {
        "public_id": "fair-tc-third-party",
        "name": "Third-party / supplier",
        "category": "FAIR threat community",
        "description": "Threats arriving via a trusted vendor or service provider — managed services, software supply chain.",
    },
    {
        "public_id": "fair-tc-natural-events",
        "name": "Natural / environmental events",
        "category": "FAIR threat community",
        "description": "Weather, fire, hardware failure cascading into outage or data loss.",
    },
    # MITRE ATT&CK Enterprise — high-frequency starter set
    {
        "public_id": "mitre-T1566",
        "name": "Phishing",
        "category": "MITRE ATT&CK · Initial Access",
        "description": "Adversaries send phishing messages to gain access — spearphishing attachment, link, or via service.",
        "references": ["https://attack.mitre.org/techniques/T1566/"],
        "attributes": {"tactic": "Initial Access", "technique_id": "T1566"},
    },
    {
        "public_id": "mitre-T1078",
        "name": "Valid Accounts",
        "category": "MITRE ATT&CK · Defense Evasion",
        "description": "Obtained credentials used to bypass access controls — default, local, domain, cloud accounts.",
        "references": ["https://attack.mitre.org/techniques/T1078/"],
        "attributes": {"technique_id": "T1078"},
    },
    {
        "public_id": "mitre-T1486",
        "name": "Data Encrypted for Impact (Ransomware)",
        "category": "MITRE ATT&CK · Impact",
        "description": "Encryption of data on target systems to interrupt availability and demand payment.",
        "references": ["https://attack.mitre.org/techniques/T1486/"],
        "attributes": {"technique_id": "T1486"},
    },
    {
        "public_id": "mitre-T1190",
        "name": "Exploit Public-Facing Application",
        "category": "MITRE ATT&CK · Initial Access",
        "description": "Initial access via a vulnerability in an internet-facing application, API or service.",
        "references": ["https://attack.mitre.org/techniques/T1190/"],
        "attributes": {"technique_id": "T1190"},
    },
    {
        "public_id": "mitre-T1567",
        "name": "Exfiltration Over Web Service",
        "category": "MITRE ATT&CK · Exfiltration",
        "description": "Stolen data exfiltrated to cloud storage or other web service to blend with normal traffic.",
        "references": ["https://attack.mitre.org/techniques/T1567/"],
        "attributes": {"technique_id": "T1567"},
    },
    {
        "public_id": "mitre-T1110",
        "name": "Brute Force",
        "category": "MITRE ATT&CK · Credential Access",
        "description": "Credentials guessed or sprayed against authentication endpoints.",
        "references": ["https://attack.mitre.org/techniques/T1110/"],
        "attributes": {"technique_id": "T1110"},
    },
    {
        "public_id": "mitre-T1059",
        "name": "Command and Scripting Interpreter",
        "category": "MITRE ATT&CK · Execution",
        "description": "Abuse of shells (PowerShell, bash, etc.) to execute attacker-controlled commands.",
        "references": ["https://attack.mitre.org/techniques/T1059/"],
        "attributes": {"technique_id": "T1059"},
    },
    {
        "public_id": "mitre-T1499",
        "name": "Endpoint Denial of Service",
        "category": "MITRE ATT&CK · Impact",
        "description": "Service outage caused by resource exhaustion or protocol abuse against an endpoint or application.",
        "references": ["https://attack.mitre.org/techniques/T1499/"],
        "attributes": {"technique_id": "T1499"},
    },
]


# ----------------------------------------------------------------- controls


CONTROLS: list[dict] = []

# NIST CSF v2.0 functions
for code, name, description in [
    ("GV", "Govern", "Establish, communicate and monitor the organization's cybersecurity risk-management strategy."),
    ("ID", "Identify", "Understand assets, suppliers, governance, risk and the cybersecurity environment."),
    ("PR", "Protect", "Safeguards to ensure delivery of critical services — identity, training, data security."),
    ("DE", "Detect", "Identify cybersecurity events as they occur — anomalies, continuous monitoring."),
    ("RS", "Respond", "Take action on detected events — response planning, communications, mitigation."),
    ("RC", "Recover", "Maintain resilience and restore capabilities or services after an incident."),
]:
    CONTROLS.append({
        "public_id": f"nist-csf-{code.lower()}",
        "framework": "NIST CSF 2.0",
        "code": code,
        "name": name,
        "description": description,
        "category": "Function",
    })

# CIS Controls v8.1 (all 18)
CIS = [
    (1, "Inventory and Control of Enterprise Assets"),
    (2, "Inventory and Control of Software Assets"),
    (3, "Data Protection"),
    (4, "Secure Configuration of Enterprise Assets and Software"),
    (5, "Account Management"),
    (6, "Access Control Management"),
    (7, "Continuous Vulnerability Management"),
    (8, "Audit Log Management"),
    (9, "Email and Web Browser Protections"),
    (10, "Malware Defenses"),
    (11, "Data Recovery"),
    (12, "Network Infrastructure Management"),
    (13, "Network Monitoring and Defense"),
    (14, "Security Awareness and Skills Training"),
    (15, "Service Provider Management"),
    (16, "Application Software Security"),
    (17, "Incident Response Management"),
    (18, "Penetration Testing"),
]
for num, name in CIS:
    CONTROLS.append({
        "public_id": f"cis-v8-{num:02d}",
        "framework": "CIS Controls v8.1",
        "code": f"CIS-{num}",
        "name": name,
        "category": "Safeguard",
    })

# ISO 27001:2022 Annex A — themes plus representative controls
ISO_THEMES = [
    ("A5", "Organizational controls", "Policies, roles, supplier relationships, intelligence."),
    ("A6", "People controls", "Screening, terms, awareness, disciplinary process."),
    ("A7", "Physical controls", "Perimeters, entry, secure areas, equipment."),
    ("A8", "Technological controls", "Endpoint, network, application, monitoring."),
]
for code, name, desc in ISO_THEMES:
    CONTROLS.append({
        "public_id": f"iso-27001-2022-{code.lower()}",
        "framework": "ISO 27001:2022",
        "code": code,
        "name": name,
        "description": desc,
        "category": "Theme",
    })

ISO_REP = [
    ("A.5.1", "Policies for information security"),
    ("A.5.7", "Threat intelligence"),
    ("A.5.23", "Information security for use of cloud services"),
    ("A.5.30", "ICT readiness for business continuity"),
    ("A.6.3", "Information security awareness, education and training"),
    ("A.6.7", "Remote working"),
    ("A.7.2", "Physical entry"),
    ("A.7.11", "Supporting utilities"),
    ("A.8.7", "Protection against malware"),
    ("A.8.8", "Management of technical vulnerabilities"),
    ("A.8.16", "Monitoring activities"),
    ("A.8.23", "Web filtering"),
    ("A.8.24", "Use of cryptography"),
    ("A.8.28", "Secure coding"),
]
for code, name in ISO_REP:
    CONTROLS.append({
        "public_id": f"iso-27001-2022-{code.lower().replace('.', '-')}",
        "framework": "ISO 27001:2022",
        "code": code,
        "name": name,
        "category": "Control",
    })


# ----------------------------------------------------------------- benchmarks


BENCHMARKS: list[dict] = [
    # FAIR-inspired starter ranges. Calibrate to your incident history in production.
    {
        "public_id": "bench-mfg-ransomware-tef",
        "name": "Manufacturing · Ransomware · TEF",
        "industry": "Manufacturing",
        "metric": "tef",
        "distribution": {"type": "pert", "min": 1, "mode": 4, "max": 12},
        "citation": "Composite reference range — calibrate to local incident history.",
    },
    {
        "public_id": "bench-retail-webapp-tef",
        "name": "Retail · Web Application Exploit · TEF",
        "industry": "Retail",
        "metric": "tef",
        "distribution": {"type": "pert", "min": 6, "mode": 18, "max": 48},
        "citation": "Composite reference range.",
    },
    {
        "public_id": "bench-healthcare-pii-plm",
        "name": "Healthcare · PII Breach · Primary Loss (per event)",
        "industry": "Healthcare",
        "metric": "plm",
        "distribution": {"type": "lognormal", "min": 200_000, "max": 6_000_000},
        "citation": "Composite reference range; magnitudes vary widely by record count.",
    },
    {
        "public_id": "bench-finance-ddos-tef",
        "name": "Financial Services · DDoS · TEF",
        "industry": "Financial Services",
        "metric": "tef",
        "distribution": {"type": "pert", "min": 4, "mode": 12, "max": 30},
        "citation": "Composite reference range.",
    },
    {
        "public_id": "bench-tech-misconfig-plm",
        "name": "Technology · Cloud Misconfig · Primary Loss",
        "industry": "Technology",
        "metric": "plm",
        "distribution": {"type": "lognormal", "min": 25_000, "max": 900_000},
        "citation": "Composite reference range.",
    },
    {
        "public_id": "bench-msp-supplier-tef",
        "name": "Cross-industry · MSP Compromise · TEF",
        "industry": "Cross-industry",
        "metric": "tef",
        "distribution": {"type": "pert", "min": 0.3, "mode": 1.0, "max": 3.0},
        "citation": "Composite reference range.",
    },
    {
        "public_id": "bench-insider-pii-slp",
        "name": "Cross-industry · Insider PII · Secondary Loss Probability",
        "industry": "Cross-industry",
        "metric": "slp_prob",
        "distribution": {"type": "pert", "min": 0.3, "mode": 0.55, "max": 0.85},
        "citation": "Composite reference range.",
    },
]


# ----------------------------------------------------------------- loader


def seed_knowledge(db: Session) -> dict[str, int]:
    counts = {"threats": 0, "controls": 0, "benchmarks": 0}

    for data in THREATS:
        if not db.exec(
            select(ThreatEntry).where(ThreatEntry.public_id == data["public_id"])
        ).first():
            db.add(ThreatEntry(source="builtin", **data))
            counts["threats"] += 1

    for data in CONTROLS:
        if not db.exec(
            select(ControlEntry).where(ControlEntry.public_id == data["public_id"])
        ).first():
            db.add(ControlEntry(source="builtin", **data))
            counts["controls"] += 1

    for data in BENCHMARKS:
        if not db.exec(
            select(BenchmarkEntry).where(BenchmarkEntry.public_id == data["public_id"])
        ).first():
            db.add(BenchmarkEntry(source="builtin", **data))
            counts["benchmarks"] += 1

    # Layer plugin-contributed knowledge on top.
    from app.plugins import registry as _plugin_registry

    for kn in _plugin_registry.knowledge:
        for data in kn.threats:
            if not db.exec(
                select(ThreatEntry).where(ThreatEntry.public_id == data["public_id"])
            ).first():
                db.add(ThreatEntry(source=kn.source, **data))
                counts["threats"] += 1
        for data in kn.controls:
            if not db.exec(
                select(ControlEntry).where(ControlEntry.public_id == data["public_id"])
            ).first():
                db.add(ControlEntry(source=kn.source, **data))
                counts["controls"] += 1
        for data in kn.benchmarks:
            if not db.exec(
                select(BenchmarkEntry).where(BenchmarkEntry.public_id == data["public_id"])
            ).first():
                db.add(BenchmarkEntry(source=kn.source, **data))
                counts["benchmarks"] += 1

    db.flush()
    return counts
