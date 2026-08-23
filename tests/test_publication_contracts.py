import pytest
from pydantic import ValidationError

from research_agent_platform.publication_contracts import (
    ManuscriptContext,
    ParagraphContract,
    RevisionChange,
    RevisionMatrix,
    StructuredFinding,
    VenueRuleSource,
    VenueStyleCard,
    VenueStyleRule,
    WritingPackage,
)


def test_writing_package_requires_traceable_source_ids():
    package = WritingPackage(
        package_id="wp-1",
        objective="draft paper",
        source_ids=["result-1"],
        evidence_ids=["PE-1"],
    )
    assert package.model_dump()["source_ids"] == ["result-1"]


def test_paragraph_contract_requires_claim_or_author_input():
    with pytest.raises(ValidationError):
        ParagraphContract(section="Results", purpose="report finding")

    contract = ParagraphContract(
        section="Results",
        purpose="report finding",
        claim="The intervention improved accuracy.",
        evidence_ids=["PE-1"],
    )
    assert contract.evidence_ids == ["PE-1"]


def test_finding_id_is_stable_and_revision_matrix_tracks_decision():
    finding = StructuredFinding(
        finding_id="f-1",
        role="methods",
        severity="major",
        category="methods",
        location="Results paragraph 2",
        concern="Missing control.",
        recommendation="Add a control.",
    )
    change = RevisionChange(
        change_id="c-1",
        finding_id=finding.finding_id,
        location="Results paragraph 2",
        before="No control.",
        after="We added a control.",
        reason="Address missing control.",
        authorization="approved",
    )
    matrix = RevisionMatrix(
        rows=[{"finding_id": finding.finding_id, "decision": "accept", "change_id": change.change_id}]
    )
    assert matrix.rows[0]["finding_id"] == "f-1"


def test_venue_style_card_requires_traceable_provenance_for_each_rule():
    source = VenueRuleSource(
        url="https://example.org/authors",
        source_type="official_guideline",
        retrieved_at="2026-08-16",
    )
    card = VenueStyleCard(
        card_id="nature-20260816",
        venue="Nature",
        language="en",
        sources=[source],
        rules=[
            VenueStyleRule(
                category="reporting",
                instruction="Include a data-availability statement when required.",
                source_urls=[source.url],
            )
        ],
    )

    assert card.rules[0].source_urls == [source.url]

    with pytest.raises(ValidationError):
        VenueStyleCard(
            card_id="untraceable",
            venue="Nature",
            language="en",
            sources=[source],
            rules=[
                VenueStyleRule(
                    category="reporting",
                    instruction="Include a data-availability statement when required.",
                    source_urls=["https://unlisted.example/rule"],
                )
            ],
        )
