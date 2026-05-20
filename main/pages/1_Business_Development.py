import streamlit as st
import pandas as pd

# ❗ ignore unresolved references — Streamlit adds main/ to sys.path
from db.mongo import init_deals_collection, get_all_deals, update_deal, STAGES

init_deals_collection()

st.title("Business Development")
st.caption("Deal pipeline — MongoDB integration test")

# --- Sidebar: refresh + filters ---
with st.sidebar:
    if st.button("🔄 Refresh"):
        st.rerun()

    st.divider()
    st.subheader("Filters")

    # Pull unique values from the full unfiltered dataset for filter options
    all_deals = get_all_deals()
    stage_options  = ["All"] + sorted({d["stage"]  for d in all_deals})
    status_options = ["All"] + sorted({d["status"] for d in all_deals})

    stage_filter  = st.selectbox("Stage",  stage_options)
    status_filter = st.selectbox("Status", status_options)

# Build filter dict from sidebar selections; empty dict = no filter
filters = {}
if stage_filter  != "All":
    filters["stage"]  = stage_filter
if status_filter != "All":
    filters["status"] = status_filter

# Re-query only if filters are active, otherwise reuse the already-fetched data
deals = get_all_deals(filters) if filters else all_deals

# --- Deals Table ---
st.subheader("Deals")
if deals:
    st.dataframe(pd.DataFrame(deals), width='stretch', hide_index=True)
else:
    st.info("No deals match the current filters.")

# --- Edit Form ---
st.divider()
st.subheader("Edit Deal")

if not all_deals:
    st.warning("No deals available to edit.")
else:
    deal_lookup = {d["deal_name"]: d for d in all_deals}

    # Dropdown is OUTSIDE the form so changing it triggers an immediate rerun,
    # allowing the form fields below to populate with the correct deal's values
    # before the user edits anything or clicks Save.
    selected_name = st.selectbox("Deal", options=list(deal_lookup.keys()))
    selected = deal_lookup[selected_name]

    with st.form("edit_deal_form"):
        new_stage = st.selectbox(
            "Stage", options=STAGES,
            index=STAGES.index(selected["stage"]) if selected["stage"] in STAGES else 0
        )
        new_city  = st.text_input("City", value=selected["city"])
        submitted = st.form_submit_button("Save")

    if submitted:
        updated = update_deal(selected["id"], stage=new_stage, city=new_city)
        if updated:
            st.success(f"'{selected_name}' → stage: '{new_stage}', city: '{new_city}'")
        else:
            st.error(f"No deal found with id {selected['id']}.")
