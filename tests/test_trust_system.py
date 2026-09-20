from datetime import datetime, timezone
import json
import shutil
import subprocess
from pathlib import Path

from commons.trust import ALLOWED_CLAIM_TYPES, evaluate_registry, load_registry


REGISTRY_PATH = Path("public/trust-registry.json")


def registry():
    return load_registry(REGISTRY_PATH)


def test_registry_is_public_machine_readable_and_versioned() -> None:
    data = registry()

    assert data["version"] == "1.0"
    assert data["methodology_version"] == "trust-v1"
    assert data["snapshot_at"] == "2026-09-20T00:00:00Z"
    assert data["sources"]
    assert data["claims"]
    assert data["evaluation_requirements"]


def test_trust_registry_is_healthy_at_its_declared_snapshot() -> None:
    data = registry()
    report = evaluate_registry(
        data,
        now=datetime.fromisoformat(data["snapshot_at"].replace("Z", "+00:00")),
    )

    assert report["status"] == "HEALTHY"
    assert report["provenance_coverage"] == 1.0
    assert report["stale_critical_claims"] == []
    assert report["missing_sources"] == []
    assert report["sources_without_limits"] == []
    assert report["unresolved_conflicts"] == []
    assert report["open_high_incidents"] == []
    assert report["invalid_claims"] == []
    assert report["missing_required_evaluators"] == []
    assert all(check["passed"] for check in report["checks"])


def test_stale_critical_claim_forces_degraded_status() -> None:
    data = registry()

    # DRC emergency counts are declared fresh for seven days from 16 Sep.
    report = evaluate_registry(
        data,
        now=datetime(2026, 9, 24, tzinfo=timezone.utc),
    )

    assert report["status"] == "DEGRADED"
    stale_ids = {claim["id"] for claim in report["stale_critical_claims"]}
    assert "drc-confirmed-cases" in stale_ids
    assert "drc-confirmed-deaths" in stale_ids
    assert "drc-recoveries" in stale_ids
    assert "drc-mixed-signals" in stale_ids


def test_every_active_claim_has_known_sources_and_limitations() -> None:
    data = registry()
    source_ids = {source["id"] for source in data["sources"]}

    for claim in data["claims"]:
        if claim["status"] != "active":
            continue
        assert claim["claim_type"] in ALLOWED_CLAIM_TYPES
        assert claim["source_ids"], claim["id"]
        assert set(claim["source_ids"]) <= source_ids
        assert claim["limitations"].strip()
        assert claim["as_of"]
        assert claim["criticality"] in {"low", "medium", "high"}


def test_every_source_declares_role_update_pattern_and_limits() -> None:
    data = registry()

    for source in data["sources"]:
        assert source["name"].strip()
        assert source["organization"].strip()
        assert source["class"] in {
            "primary_authority",
            "official_data_provider",
            "reference_dataset",
        }
        assert source["domain"].strip()
        assert source["url"].startswith("https://")
        assert source["update_pattern"].strip()
        assert source["limitations"].strip()


def test_observation_inference_and_proposal_are_explicitly_separated() -> None:
    data = registry()

    assert set(data["claim_types"]) == ALLOWED_CLAIM_TYPES

    drc_safety = next(
        claim for claim in data["claims"]
        if claim["id"] == "drc-no-direct-public-action"
    )
    assert drc_safety["claim_type"] == "proposed"
    assert "product safety decision" in drc_safety["limitations"]


def test_current_authority_ceiling_locks_execution_levels() -> None:
    data = registry()
    levels = {item["level"]: item for item in data["capability_levels"]}

    assert levels["L0"]["enabled"] is True
    assert levels["L1"]["enabled"] is True
    assert levels["L2"]["enabled"] is True
    assert levels["L3"]["enabled"] is True
    assert levels["L4"]["enabled"] is False
    assert levels["L5"]["enabled"] is False
    assert "consequential" in levels["L5"]["description"].lower()
    assert "human authorization" in levels["L5"]["description"].lower()


def test_correction_policy_forbids_silent_overwrite() -> None:
    policy = registry()["correction_policy"]

    assert policy["public_log"] is True
    assert policy["preserve_history"] is True
    assert policy["silent_overwrite"] is False


def test_incident_history_preserves_real_ui_failure_and_prevention() -> None:
    incidents = registry()["incidents"]
    incident = next(
        item for item in incidents
        if item["id"] == "ui-containment-regression-2026-09-19"
    )

    assert incident["status"] == "resolved"
    assert incident["severity"] == "medium"
    assert "unmatched CSS brace" in incident["root_cause"]
    assert "brace-balance" in incident["correction"]
    assert "containment" in incident["prevention"]


def test_browser_trust_evaluator_has_hard_degraded_mode() -> None:
    trust_js = Path("public/trust.js").read_text(encoding="utf-8")

    assert 'status:"DEGRADED"' in trust_js
    assert 'cache:"no-store"' in trust_js
    assert 'if(!registry)return degradedState("Trust registry unavailable")' in trust_js
    assert 'provenanceCoverage===1' in trust_js
    assert "staleCriticalClaims.length===0" in trust_js
    assert "unresolvedConflicts.length===0" in trust_js
    assert "openHighIncidents.length===0" in trust_js


def test_browser_evaluator_checks_action_safety_not_just_claims() -> None:
    trust_js = Path("public/trust.js").read_text(encoding="utf-8")

    assert 'id:"action-causality"' in trust_js
    assert 'id:"external-action-verification"' in trust_js
    assert 'id:"no-invented-action"' in trust_js
    assert "item.causalClaim!==true" in trust_js
    assert 'item.type==="external" && item.actionability==="DIRECT"' in trust_js


def test_trust_center_exposes_status_claims_sources_evaluations_incidents() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert 'id="trustSnapshot"' in page
    assert 'id="trustCenter"' in page
    for tab in ("status", "claims", "sources", "evaluations", "incidents"):
        assert f'data-trust-tab="{tab}"' in page

    assert "function loadTrustSystem" in app
    assert "function evaluateTrustNow" in app
    assert "function renderTrustClaimsTab" in app
    assert "function renderTrustSourcesTab" in app
    assert "function renderTrustEvaluationsTab" in app
    assert "function renderTrustIncidentsTab" in app
    assert 'openTrustCenter("claims","audit")' in app

    assert "COMMONS TRUST CENTER" in styles
    assert ".trust-center:not(.open)" in styles
    assert ".trust-snapshot[data-status=\"DEGRADED\"]" in styles


def test_evidence_drawer_can_open_machine_readable_claim_ledger() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert "Inspect the claim ledger" in app
    assert 'id="evidenceTrustBtn"' in app
    assert 'window.COMMONS_TRUST.sourceById' in app
    assert "freshness window" in app


def test_action_layer_never_silently_verifies_external_completion() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")
    loops = Path("public/action-loops.js").read_text(encoding="utf-8")

    assert "WORLD PULSE cannot see the external transaction." in app
    assert 'verification:"self_reported"' in app
    assert "It does not prove your action caused the outcome." in app
    assert "WORLD PULSE cannot verify your payment" in loops


def test_no_verified_action_state_is_preserved_for_drc() -> None:
    loops = Path("public/action-loops.js").read_text(encoding="utf-8")

    assert 'statusLabel: "No verified public action invented"' in loops
    assert "resist inventing an action" in loops
    assert 'actionability: "INFORMATION"' in loops


def test_trust_javascript_and_registry_parse() -> None:
    json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    node = shutil.which("node")
    if node is None:
        return

    result = subprocess.run(
        [node, "--check", "public/trust.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_direct_external_action_is_blocked_when_story_trust_fails() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert "function trustGateForStory" in app
    assert "function interventionTrustGate" in app
    assert "Trust registry unavailable. Direct external action is disabled." in app
    assert "critical claim(s) for this story are stale" in app
    assert "missing source reference" in app
    assert "A high-severity trust incident is open." in app
    assert "Unavailable until trust checks pass" in app
    assert "if(!gate.allowed)" in app
    assert ".intervention-card.trust-blocked" in styles
    assert ".word-button:disabled" in styles


def test_trust_status_is_computed_not_hardcoded_in_ui() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert 'id="trustSnapshotStatus">CHECKING</strong>' in page
    assert '$("trustSnapshotStatus").textContent=trustReport.status' in app
    assert "Math.round((trustReport.provenanceCoverage||0)*100)" in app
    assert "trustReport.staleCriticalClaims" in app
    assert "trustReport.unresolvedConflicts" in app
    assert "trustReport.passedChecks" in app


def test_operator_trust_cli_exists_and_uses_same_registry_evaluator() -> None:
    script = Path("scripts/trust_report.py").read_text(encoding="utf-8")

    assert "from commons.trust import evaluate_registry, load_registry" in script
    assert 'default="public/trust-registry.json"' in script
    assert 'return 0 if report["status"] == "HEALTHY" else 2' in script


def test_trust_documentation_states_current_limits() -> None:
    doc = Path("docs/COMMONS_TRUST_V1.md").read_text(encoding="utf-8")

    assert "Reliability constitution" in doc
    assert "Never fabricate reality." in doc
    assert "Human authority scales with consequence." in doc
    assert "Fail visibly and safely." in doc
    assert "cryptographically signed source attestations" in doc
    assert "independent third-party audit" in doc


def test_calm_orientation_is_computed_from_live_product_state() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert 'id="calmOrientation"' in page
    assert 'id="orientationStories"' in page
    assert 'id="orientationImproving"' in page
    assert 'id="orientationActions"' in page
    assert 'id="orientationStale"' in page
    assert "See what matters. Leave when you’re oriented." in page

    assert "function renderCalmOrientation" in app
    assert "STORIES.length" in app
    assert "trustGateForStory(story.id).allowed" in app
    assert "trustReport.staleCriticalClaims" in app

    assert ".calm-orientation" in styles
    assert ".calm-metric" in styles


def test_trust_center_defaults_to_simple_progressive_disclosure() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert 'id="trustModeSimple"' in page
    assert 'id="trustModeAudit"' in page
    assert 'let trustMode = "simple"' in app
    assert "function renderTrustSimpleTab" in app
    assert "function setTrustMode" in app
    assert 'openTrustCenter("status","simple")' in app
    assert 'setTrustMode("audit","claims")' in app

    assert '.trust-center[data-mode="simple"]' in styles
    assert '.trust-center[data-mode="audit"]' in styles
    assert '.trust-center[data-mode="simple"] .audit-only{display:none}' in styles


def test_simple_trust_mode_explains_status_before_showing_full_audit() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert "Healthy does not mean infallible." in app
    assert "We can trace the claims" in app
    assert "The critical evidence is current" in app
    assert "Disagreements are not hidden" in app
    assert "The safety checks pass" in app
    assert "WHAT WE CURRENTLY KNOW" in app
    assert "the three claims that shape this case" in app
    assert "Open the full evidence file →" in app


def test_trust_inspection_recomposes_story_instead_of_only_covering_it() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert 'document.body.classList.add("trust-inspection")' in app
    assert 'document.body.classList.remove("trust-inspection","trust-audit")' in app
    assert 'document.body.classList.toggle("trust-audit",trustMode==="audit")' in app

    assert "body.trust-inspection #globe" in styles
    assert "body.trust-inspection .scroll-narrative" in styles
    assert "body.trust-inspection .story-head" in styles
    assert "body.trust-inspection .time-instrument" in styles
    assert "--trust-panel-width" in styles


def test_audit_claims_are_more_readable_but_keep_all_limits() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert "What to keep in mind" in app
    assert '.trust-center[data-mode="audit"] .claim-card' in styles
    assert '.trust-center[data-mode="audit"] .claim-statement' in styles
    assert '.trust-center[data-mode="audit"] .claim-limits' in styles


def test_simple_mode_status_is_less_dense_than_audit_mode() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert 'if(trustMode==="simple")' in app
    assert "trust-simple-statusbar" in app
    assert "trust-status-grid" in app
    assert ".trust-simple-statusbar" in styles
    assert ".trust-proof-list" in styles


def test_action_loop_is_presented_as_guided_case_file() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert "COMMONS · CASE FILE" in page
    assert "Current case" in page
    assert "My action notes" in page

    assert "function renderInvestigationActor" in app
    assert "function renderIntervention" in app
    assert "Who is on the ground?" in app
    assert "Start with the strongest verified path." in app
    assert "WHAT WE STILL NEED TO LEARN" in app
    assert "EVIDENCE DESK" in app

    assert ".case-hero" in styles
    assert ".case-section" in styles
    assert ".case-action.primary" in styles
    assert ".case-primary-button" in styles
    assert ".case-questions" in styles


def test_action_language_is_human_readable_not_internal_jargon() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert "What supports this" in app
    assert "What we still don’t know" in app
    assert "What we’ll look for next" in app
    assert "BEST VERIFIED NEXT MOVE" in app
    assert "KEEP THE LOOP OPEN" in app
    assert "HELP THE EVIDENCE TRAVEL" in app


def test_trust_is_presented_as_investigative_evidence_desk() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")
    app = Path("public/app.js").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert "COMMONS · EVIDENCE DESK" in page
    assert "Here’s what we know." in page
    assert "Trust must be inspectable." in page

    assert "function claimWhyItMatters" in app
    assert "function renderInvestigativeClaim" in app
    assert "Why this matters" in app
    assert "What to keep in mind" in app
    assert "WHAT WE CURRENTLY KNOW" in app
    assert "WHAT THIS DOESN’T PROVE" in app

    assert ".investigation-intro" in styles
    assert ".trust-story-claim" in styles
    assert ".claim-meaning" in styles
    assert ".claim-limit" in styles


def test_audit_separates_current_case_from_other_atlas_claims() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert "CURRENT CASE NOTES" in app
    assert "OTHER STORIES IN THE ATLAS" in app
    assert "These claims remain part of the same public ledger" in app
    assert "claim.story_id===activeStory.id" in app
    assert "claim.story_id!==activeStory.id" in app


def test_investigative_design_raises_readability_floor() -> None:
    styles = Path("public/styles.css").read_text(encoding="utf-8")

    assert "--ink:#080806" in styles
    assert "--bone:#f2eee4" in styles
    assert ".case-lede" in styles
    assert "font-size:16px" in styles
    assert ".investigative-claim .claim-statement" in styles
    assert "font-size:18px!important" in styles
    assert ".trust-proof b{font-size:12px}" in styles
