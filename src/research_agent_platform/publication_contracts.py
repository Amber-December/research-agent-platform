from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class WritingPackage(BaseModel):
    package_id: str
    objective: str
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    resource_versions: dict[str, str] = Field(default_factory=dict)


class ManuscriptContext(BaseModel):
    manuscript_id: str
    discipline: str = "general"
    language: str = "en"
    article_type: str = "research_article"
    venue: str | None = None
    writing_package_id: str
    style_guide_id: str | None = None


class VenueRuleSource(BaseModel):
    url: str
    source_type: Literal[
        "official_guideline",
        "publisher_policy",
        "reporting_guideline",
        "user_template",
        "open_exemplar",
    ]
    retrieved_at: str = ""


class VenueStyleRule(BaseModel):
    category: str
    instruction: str
    source_urls: list[str] = Field(min_length=1)
    status: Literal["verified", "needs_author_confirmation"] = "verified"


class VenueStyleCard(BaseModel):
    card_id: str
    venue: str
    language: Literal["zh", "en"]
    sources: list[VenueRuleSource] = Field(default_factory=list)
    rules: list[VenueStyleRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def rules_must_reference_listed_sources(self) -> "VenueStyleCard":
        known_urls = {source.url for source in self.sources}
        for rule in self.rules:
            if not set(rule.source_urls).issubset(known_urls):
                raise ValueError("venue style rule references an unlisted source")
        return self


class ParagraphContract(BaseModel):
    section: str
    purpose: str
    claim: str | None = None
    author_input_needed: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    prohibited_inferences: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_claim_or_input(self) -> "ParagraphContract":
        if not self.claim and not self.author_input_needed:
            raise ValueError("paragraph contract requires claim or author_input_needed")
        return self


class StructuredFinding(BaseModel):
    finding_id: str
    role: str
    severity: Literal["blocking", "major", "minor", "suggestion"]
    category: str
    location: str
    concern: str
    recommendation: str
    evidence_ids: list[str] = Field(default_factory=list)


class RevisionChange(BaseModel):
    change_id: str
    finding_id: str | None = None
    location: str
    before: str
    after: str
    reason: str
    source: str = "author_request"
    authorization: Literal["pending", "approved", "rejected", "author_input_needed"] = "pending"


class RevisionMatrix(BaseModel):
    rows: list[dict[str, str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rows(self) -> "RevisionMatrix":
        valid = {"accept", "partial", "reject", "author_input_needed", "pending"}
        for row in self.rows:
            if not row.get("finding_id"):
                raise ValueError("revision matrix row requires finding_id")
            if row.get("decision") not in valid:
                raise ValueError("revision matrix row has invalid decision")
        return self
