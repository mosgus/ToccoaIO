from google import genai
from google.genai import types
import anthropic
from datetime import datetime
from pathlib import Path
import re

# Clanker API Init.

    # Ms. Gemini
try:
    with open("./keys/gemini_key.txt", "r") as f:
        _gemini_key = f.read().strip()
except FileNotFoundError:
    import streamlit as st
    _gemini_key = st.secrets["GEMINI_KEY"]
    
    # Mr. Claude
try:
    with open("./keys/claude_key.txt", "r") as f:
        _claude_key = f.read().strip()
except FileNotFoundError:
    import streamlit as st
    _claude_key = st.secrets["CLAUDE_KEY"]

gem_client = genai.Client(api_key=_gemini_key)
claude_client = anthropic.Anthropic(api_key=_claude_key)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = PROJECT_ROOT / "analysis"


def research_property(address: str, business_name: str) -> dict:
    """Use Gemini with Google Search grounding to gather raw property and tenant intelligence.

    Returns a dict with:
        "research": str  — structured findings with inline citation numbers [1], [2], ...
        "sources":  list — [{"title": str, "url": str}, ...] extracted from grounding metadata
    """

    # Branch prompt based on whether a tenant was provided
    tenant_section = f"""
    2. **Tenant / Business News**
   - Recent news about {business_name} at this location or in this market
   - Any closures, expansions, relocations, or financial stress signals
   - Lease renewals or new lease announcements if found""" if business_name else \
    """2. **Vacancy & Listing Status**
   - Any active for-sale or for-lease listings at this address
   - Listing broker or contact if findable
   - How long the property appears to have been vacant or on market
   - Prior tenants at this address
   """

    tenant_line = f"Tenant / Business: {business_name}" if business_name else "Tenant / Business: Unknown / Vacant"

    # Build the research prompt targeting the four key data categories
    prompt = f"""
Search the web and return structured findings for the following commercial real estate property:

Address: {address}
{tenant_line}

Please research and report on each of the following areas:

1. **Building Permits & Notice of Commencement (NOC)**
   - Any recent building permits filed for this address
   - Any Notice of Commencement filings
   - Dates, scope of work, permit status if available

{tenant_section}

3. **Property Type & Use**
   - What type of commercial property this appears to be (retail strip, standalone, mixed-use, etc.)
   - Approximate size, age, or configuration if findable
   - Current or past tenants at this address

4. **Public Records**
   - Any tax liens or delinquent taxes on this property
   - Zoning changes or variance requests
   - Recent sales history or ownership transfers
   - Any litigation or code violations

When citing a source, place a numbered reference inline like [1] or [2] immediately after the claim.
If you cannot find information for a category, state that explicitly.
"""

    # Call Gemini with Google Search tool enabled for live web grounding
    response = gem_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    # Extract grounding source URLs from response metadata
    sources = []
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks
        for chunk in chunks:
            if chunk.web:
                sources.append({"title": chunk.web.title or "", "url": chunk.web.uri or ""})
    except (AttributeError, IndexError):
        pass  # Grounding metadata unavailable — sources will be empty

    return {"research": response.text, "sources": sources}


def synthesize_report(address: str, business_name: str, gemini_research: str, sources: list = None) -> str:
    """Pass Gemini's raw research to Claude to produce a structured analyst report."""

    # Swap the second section based on occupancy status
    if business_name:
        second_section = f"""**Tenant Health**
Assess the financial and operational health of {business_name} at this location based on any available signals."""
        subject_line = f"**Tenant / Business:** {business_name}"
    else:
        second_section = """**Vacancy & Marketability**
Assess the vacancy situation — how long it appears to have been vacant, whether it is actively listed, asking terms if findable, and how marketable this asset is to future tenants."""
        subject_line = "**Tenant / Business:** Vacant / Unknown"

    # Build an optional numbered source list to inject into Claude's prompt
    import json
    sources_block = ""
    if sources:
        sources_block = f"\n**Sources (numbered inline in the research above):**\n```json\n{json.dumps(sources, indent=2)}\n```\n"

    # Prompt Claude to act as a CRE lending analyst and organize findings into a credit memo format
    prompt = f"""You are a senior commercial real estate lending analyst preparing a credit intelligence memo.

A property research agent has gathered the following raw data on a subject property. Your job is to synthesize this into a structured report for a credit officer.

**Subject Property:** {address}
{subject_line}

---
**Raw Research Data:**
{gemini_research}
{sources_block}---

Produce a structured report with exactly these five labeled sections. Use bold markdown headers for each section name:

**Property Overview**
Describe what this asset appears to be based on the research — type, location context, likely use class.

{second_section}

**Red Flags**
List anything a commercial lender should be concerned about — permit activity suggesting construction risk, vacancy duration, liens, zoning issues, etc. Be specific.

**Positive Signals**
List anything that supports the creditworthiness or stability of this asset — location quality, recent investment, strong prior tenancy, active listing activity, etc.

**Analyst Summary**
Write 2-3 sentences providing a bottom-line assessment a credit officer can act on. Include your overall risk read and any recommended due diligence items.

Be direct and analytical. If the research is insufficient to make a confident assessment, say so clearly in the relevant section.
"""

    # Call Claude Haiku to synthesize and structure the final analyst report
    response = claude_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


def save_analyst_report_md(address: str, business_name: str, analyst_report: str,
                           gemini_research: str = "", sources: list = None) -> Path:
    """Save the analyst report to /analysis as a timestamped .md file."""
    import json

    ANALYSIS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", f"{address}_{business_name}").strip("_").lower()[:120]
    output_path = ANALYSIS_DIR / f"{timestamp}_{slug}.md"

    header = (
        f"# Analyst Report\n\n"
        f"**Property Address:** {address}  \n"
        f"**Tenant / Business:** {business_name}  \n"
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
    )

    sources_section = ""
    if sources:
        sources_section = (
            f"\n\n---\n\n## Sources\n\n"
            f"```json\n{json.dumps(sources, indent=2)}\n```"
        )

    research_section = (
        f"\n\n---\n\n## Raw Gemini Research\n\n"
        f"*Source data returned by Gemini Search — inline numbers correspond to the Sources list above.*\n\n"
        f"{gemini_research}"
    ) if gemini_research else ""

    output_path.write_text(header + analyst_report + sources_section + research_section, encoding="utf-8")

    return output_path
