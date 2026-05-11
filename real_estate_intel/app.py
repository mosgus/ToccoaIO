import streamlit as st
from backend import research_property, save_analyst_report_md, synthesize_report

print("ex addy: 3065 Peachtree Industrial Blvd")
print("ex tenant: Courtland Health Care Services")
# --- Page Configuration ---
st.set_page_config(
    page_title="Toccoa.IO {Proto 1}",
    page_icon="🏢",
    layout="centered"
)

st.title("Toccoa.io {Proto 1.0}")
st.caption("AI-powered commercial property and tenant research for credit analysts")

# --- Input Fields ---
address = st.text_input(
    "Property Address",
    placeholder="e.g. 123 Main St, Atlanta, GA"
)
business_name = st.text_input(
    "Tenant / Business Name (optional — leave blank for vacant/listed properties)",
    placeholder="e.g. Walgreens"
)

# --- Run Analysis Button ---
run = st.button("Run Analysis", type="primary", disabled=not address)

# --- Analysis Execution and Results Display ---
if run:
    try:
        # Step 1: Gemini web research
        with st.spinner("Researching property..."):
            gemini_result = research_property(address, business_name)
            gemini_output = gemini_result["research"]
            sources = gemini_result["sources"]

        # Step 2: Claude synthesis into structured analyst report
        with st.spinner("Synthesizing analyst report..."):
            analyst_report = synthesize_report(address, business_name, gemini_output, sources)

        saved_report_path = save_analyst_report_md(address, business_name, analyst_report, gemini_output, sources)

        # Display the structured report with markdown rendering for bold headers
        st.divider()
        st.subheader(f"Analyst Report — {address}")
        st.markdown(analyst_report)
        st.caption(f"Saved report: {saved_report_path}")

        # Expander for raw Gemini data as an audit trail for analysts
        with st.expander("Raw Gemini Research Data"):
            st.caption("Source data returned by Gemini Search — inline [N] numbers correspond to the sources list below.")
            st.markdown(gemini_output)
            if sources:
                st.subheader("Sources")
                for i, s in enumerate(sources, 1):
                    st.markdown(f"**[{i}]** [{s['title'] or s['url']}]({s['url']})")

    except Exception as e:
        st.error(f"Analysis failed: {e}")
