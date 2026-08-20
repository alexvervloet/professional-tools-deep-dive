"""
Chapter 2 shared pieces: the schema, the rules, and the messy inputs.

One extraction task, defined once, so all three approaches (hand-rolled,
Instructor, provider-native) compete on identical ground:

  - JobPosting: the Pydantic model. Ported from the prompt-engineering dive's
    example 02, where the same schema lived as a block of prose *inside the
    prompt*. Field descriptions here mirror that prose; Instructor and the
    native mode send them to the model as the schema; the hand-rolled version
    renders them back into a prompt block (schema_block()).
  - SYSTEM_RULES: the normalization policy. Identical for every approach 
    the comparison is about how the SCHEMA travels, not about prompt quality.
  - POSTINGS: five real-shaped postings, each with a trap the schema has to
    survive (an hourly rate that must NOT become an annual salary, a hybrid
    role that is not remote, a date written in Norwegian prose, ...).
"""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

# --- The normalization policy, shared verbatim by all three approaches. -----
SYSTEM_RULES = """\
You are a precise extraction engine.
NORMALIZATION RULES:
- salary_min/salary_max are ANNUAL amounts in the posting's currency, as plain
  integers ("80-95k EUR" -> 80000 / 95000 / "EUR"). If only an hourly, daily,
  or monthly rate is given, leave salary fields and currency null.
- remote is true only for fully remote roles; hybrid or onsite -> false.
- apply_by must be an ISO date (YYYY-MM-DD); if the posting gives no explicit
  calendar date, use null. Convert written-out dates to ISO.
- skills are lowercase, deduplicated, required and nice-to-have together.
- If a field is not stated, use null. Do NOT guess."""


class Seniority(str, Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"


class JobPosting(BaseModel):
    title: str = Field(description="The job title as posted.")
    seniority: Seniority | None = Field(description="Level, if stated.")
    remote: bool = Field(description="True only if fully remote.")
    location_note: str | None = Field(description="Timezone/region/onsite constraints.")
    salary_min: int | None = Field(description="Annual minimum, integer.")
    salary_max: int | None = Field(description="Annual maximum, integer.")
    currency: str | None = Field(
        pattern=r"^[A-Z]{3}$", description="3-letter ISO code, e.g. 'EUR'."
    )
    skills: list[str] = Field(description="Lowercase, deduplicated.")
    min_years_exp: int | None = Field(description="Minimum years of experience.")
    apply_by: date | None = Field(description="ISO date, or null if no explicit date.")
    contact_email: str | None = Field(description="Contact email, if any.")


def schema_block() -> str:
    """The hand-rolled version's schema-as-prose, generated from the model so
    the two stay in sync; this block is what the dives wrote by hand."""
    lines = ["Return ONLY JSON with exactly these keys:"]
    for name, field in JobPosting.model_fields.items():
        lines.append(f"  {name}: {field.description}")
    lines.append('  (seniority must be one of "junior", "mid", "senior", "lead", or null)')
    return "\n".join(lines)


POSTINGS: dict[str, str] = {
    "baseline (the dive's own)": """\
We're hiring a Senior Backend Engineer (Remote, EU timezones). Comp: 80-95k EUR
plus equity. You'll work in Python and Go on our payments platform. 5+ yrs exp.
Nice to have: Kubernetes. Apply by 2026-07-15. Contact jobs@fintechco.eu.""",
    "hourly-rate trap": """\
Contract Data Engineer needed ASAP. $85/hr on W2, 6-month contract, fully
remote (US only). Must know SQL, dbt and Airflow. Send resume to
recruiting@datastaffing.com.""",
    "hybrid + no-comp trap": """\
Mid-level Frontend Developer, React/TypeScript. Hybrid: 2 days a week in our
Amsterdam office. Competitive salary. At least 3 years experience with modern
frontend tooling. We'd love it if you know Storybook too.""",
    "prose-date + GBP trap": """\
Lead Platform Engineer, London (hybrid, 1 day/wk onsite). £95k to £110k DOE.
Terraform, AWS and Go essential; Kafka a plus. 7+ years experience. Apply by
the 31st of August 2026 via careers@ukfintech.co.uk.""",
    "foreign-language trap": """\
Vi søker en junior utvikler! Oslo-kontor (ikke remote). Lønn: kr 600 000 –
700 000 (NOK) per år. Du kan Java eller Kotlin. Søknadsfrist: 15. august 2026.
Kontakt: jobb@norskfirma.no.""",
}
