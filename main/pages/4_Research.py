import streamlit as st

# ❗ignore unresolved references. Streamlit adds main to sys.path❗
from LLM_service import research_property, save_analyst_report_md, synthesize_report

st.title("Property Research")
st.caption("Property and tenant research and report synthesizer. Powered by Gemini(Researcher) and Claude(Reporter) APIs.")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

address = st.text_input(
    "Property Address",
    placeholder="e.g. 123 Main St, Atlanta, GA"
)
business_name = st.text_input(
    "Tenant / Business Name (optional — leave blank for vacant/listed properties)",
    placeholder="e.g. Walgreens"
)

run = st.button("Run Analysis", type="primary", disabled=not address)

if run:
    try:
        with st.spinner("Researching property..."):
            gemini_result = research_property(address, business_name)
            gemini_output = gemini_result["research"]
            sources = gemini_result["sources"]

        with st.spinner("Synthesizing analyst report..."):
            analyst_report = synthesize_report(address, business_name, gemini_output, sources)

        saved_report_path = save_analyst_report_md(address, business_name, analyst_report, gemini_output, sources)

        st.session_state.analysis_result = {
            "address": address,
            "business_name": business_name,
            "analyst_report": analyst_report,
            "gemini_output": gemini_output,
            "sources": sources,
            "saved_report_path": saved_report_path,
        }

    except Exception as e:
        st.error(f"Analysis failed: {e}")

result = st.session_state.analysis_result
if result:
    st.divider()
    st.subheader(f"Analyst Report — {result['address']}")

    st.download_button(
        label="Download Report",
        data=result["saved_report_path"].read_text(encoding="utf-8"),
        file_name=result["saved_report_path"].name,
        mime="text/markdown",
        icon=":material/download:"
    )

    st.markdown(result["analyst_report"])
    st.caption(f"Saved report: {result['saved_report_path']}")

    with st.expander("Raw Gemini Research Data"):
        st.caption("Source data returned by Gemini Search — inline [N] numbers correspond to the sources list below.")
        st.markdown(result["gemini_output"])
        if result["sources"]:
            st.subheader("Sources")
            for i, s in enumerate(result["sources"], 1):
                st.markdown(f"**[{i}]** [{s['title'] or s['url']}]({s['url']})")
