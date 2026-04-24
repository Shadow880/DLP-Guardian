import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import json
import pandas as pd
import streamlit as st

from engine.role_engine import load_user_roles, set_user_role, VALID_ROLES
from engine.site_policy_engine import load_site_policies, upsert_site_policy, delete_site_policy, VALID_MODES

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "logs" / "ai_policy_audit.log"

st.set_page_config(page_title="DLP Governance Dashboard", layout="wide")
st.title("DLP Governance Dashboard")


def load_logs():
    if not LOG_PATH.exists():
        return pd.DataFrame()

    rows = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                decision = obj.get("decision", {}) or {}
                matched_rule = decision.get("matched_rule", {}) or {}
                site_policy = decision.get("site_policy", {}) or {}

                rows.append({
                    "timestamp": obj.get("timestamp", ""),
                    "user": obj.get("user", "unknown"),
                    "source": obj.get("source", "unknown"),
                    "channel": obj.get("channel", "unknown"),
                    "text": obj.get("text", ""),
                    "action": decision.get("action", ""),
                    "allowed": decision.get("allowed", ""),
                    "reason": decision.get("reason", ""),
                    "message": decision.get("message", ""),
                    "role": decision.get("role", "employee"),
                    "role_adjustment": decision.get("role_adjustment", "none"),
                    "site_mode": site_policy.get("mode", ""),
                    "site_adjustment": decision.get("site_adjustment", "none"),
                    "rule_id": matched_rule.get("id", ""),
                    "rule_title": matched_rule.get("title", ""),
                    "rule_type": matched_rule.get("type", ""),
                    "severity": matched_rule.get("severity", ""),
                    "similarity": decision.get("semantic_score", matched_rule.get("similarity", 0)),
                    "detection_source": decision.get("detection_source", ""),
                    "pattern_hits": decision.get("pattern_hits", []),
                    "pattern_score": decision.get("pattern_score", 0),
                    "semantic_score": decision.get("semantic_score", 0),
                    "context_score": decision.get("context_score", 0),
                    "fuzzy_score": decision.get("fuzzy_score", 0),
                    "risk_score": decision.get("risk_score", 0),
                    "redaction_available": decision.get("redaction_available", False),
                    "redacted_text": decision.get("redacted_text", ""),
                })
            except Exception:
                continue

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    df.insert(0, "case_no", list(range(len(df), 0, -1)))
    return df


df = load_logs()

if df.empty:
    st.warning("No log data found yet.")
    st.stop()

for col in ["risk_score", "pattern_score", "semantic_score", "similarity", "context_score", "fuzzy_score"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

st.caption(f"Total rows loaded from log: {len(df)}")

# Build filter options first
action_options = sorted([x for x in df["action"].dropna().unique().tolist() if x != ""])
severity_options = sorted([x for x in df["severity"].dropna().unique().tolist() if x != ""])
source_options = sorted([x for x in df["source"].dropna().unique().tolist() if x != ""])
detection_options = sorted([x for x in df["detection_source"].dropna().unique().tolist() if x != ""])
role_options = sorted([x for x in df["role"].dropna().unique().tolist() if x != ""])

top1, top2 = st.columns([1, 1])

with top1:
    if st.button("Refresh Dashboard", width="stretch"):
        st.rerun()

with top2:
    if st.button("Clear Filter State", width="stretch"):
        st.session_state["flt_actions"] = action_options
        st.session_state["flt_severity"] = severity_options
        st.session_state["flt_source"] = source_options
        st.session_state["flt_detection"] = detection_options
        st.session_state["flt_roles"] = role_options
        st.session_state["flt_redaction"] = "All"
        st.session_state["flt_rows"] = "All"
        st.session_state["flt_search"] = ""
        st.rerun()

st.sidebar.header("Filters")

selected_actions = st.sidebar.multiselect(
    "Action", action_options, default=action_options, key="flt_actions"
)
selected_severities = st.sidebar.multiselect(
    "Severity", severity_options, default=severity_options, key="flt_severity"
)
selected_sources = st.sidebar.multiselect(
    "Source", source_options, default=source_options, key="flt_source"
)
selected_detection = st.sidebar.multiselect(
    "Detection Source", detection_options, default=detection_options, key="flt_detection"
)
selected_roles = st.sidebar.multiselect(
    "Role", role_options, default=role_options, key="flt_roles"
)
redaction_filter = st.sidebar.selectbox(
    "Redaction Available", ["All", "Yes", "No"], key="flt_redaction"
)
rows_to_show = st.sidebar.selectbox(
    "Rows to Show", [25, 50, 100, 250, 500, "All"], index=5, key="flt_rows"
)
search_text = st.sidebar.text_input(
    "Search prompt text", key="flt_search"
)

filtered_df = df.copy()

if selected_actions:
    filtered_df = filtered_df[
        filtered_df["action"].isin(selected_actions) | filtered_df["action"].isna() | (filtered_df["action"] == "")
    ]

if selected_severities:
    filtered_df = filtered_df[
        filtered_df["severity"].isin(selected_severities) | filtered_df["severity"].isna() | (filtered_df["severity"] == "")
    ]

if selected_sources:
    filtered_df = filtered_df[
        filtered_df["source"].isin(selected_sources) | filtered_df["source"].isna() | (filtered_df["source"] == "")
    ]

if selected_detection:
    filtered_df = filtered_df[
        filtered_df["detection_source"].isin(selected_detection) | filtered_df["detection_source"].isna() | (filtered_df["detection_source"] == "")
    ]

if selected_roles:
    filtered_df = filtered_df[
        filtered_df["role"].isin(selected_roles) | filtered_df["role"].isna() | (filtered_df["role"] == "")
    ]

if redaction_filter == "Yes":
    filtered_df = filtered_df[filtered_df["redaction_available"] == True]
elif redaction_filter == "No":
    filtered_df = filtered_df[filtered_df["redaction_available"] == False]

if search_text.strip():
    filtered_df = filtered_df[
        filtered_df["text"].fillna("").str.contains(search_text, case=False, na=False)
    ]

filtered_df = filtered_df.reset_index(drop=True)
display_logs_df = filtered_df.copy()

if rows_to_show != "All":
    display_logs_df = display_logs_df.head(int(rows_to_show)).reset_index(drop=True)

total_checks = len(filtered_df)
allow_count = int((filtered_df["action"] == "allow").sum())
warn_count = int((filtered_df["action"] == "warn").sum())
block_count = int((filtered_df["action"] == "block").sum())
avg_risk = round(float(filtered_df["risk_score"].mean()), 2) if total_checks > 0 else 0.0

st.caption(f"Filtered rows: {len(filtered_df)} | Display rows: {len(display_logs_df)}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Analytics", "Recent Logs", "Detailed Review", "Role Management", "Site Management"]
)

with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Checks", total_checks)
    c2.metric("Allowed", allow_count)
    c3.metric("Warnings", warn_count)
    c4.metric("Blocked", block_count)
    c5.metric("Avg Risk Score", avg_risk)

    st.markdown("---")

    a1, a2 = st.columns(2)
    with a1:
        st.subheader("Action Distribution")
        chart = filtered_df["action"].value_counts().rename_axis("action").reset_index(name="count")
        if not chart.empty:
            st.bar_chart(chart.set_index("action"))
    with a2:
        st.subheader("Detection Source Distribution")
        chart = filtered_df["detection_source"].value_counts().rename_axis("detection_source").reset_index(name="count")
        if not chart.empty:
            st.bar_chart(chart.set_index("detection_source"))

with tab2:
    table_df = display_logs_df.copy()
    table_df["text_preview"] = table_df["text"].fillna("").apply(lambda x: x[:160] + "..." if len(x) > 160 else x)
    table_df["pattern_hits_display"] = table_df["pattern_hits"].apply(
        lambda x: ", ".join([item.get("type", "") for item in x]) if isinstance(x, list) else ""
    )

    table_df = table_df[
        [
            "case_no", "timestamp", "user", "role", "source", "site_mode", "action",
            "severity", "rule_title", "semantic_score", "pattern_score", "risk_score",
            "detection_source", "role_adjustment", "site_adjustment",
            "pattern_hits_display", "text_preview"
        ]
    ].rename(columns={
        "case_no": "case",
        "rule_title": "matched_rule",
        "pattern_hits_display": "pattern_hits"
    })

    st.subheader("Recent Decisions")
    st.caption(f"Showing {len(display_logs_df)} of {len(filtered_df)} filtered records")
    st.dataframe(table_df, width="stretch", height=700, hide_index=True)

with tab3:
    st.subheader("Detailed Record Review")
    if display_logs_df.empty:
        st.info("No records available.")
    else:
        options = [
            f"{row['case_no']} | {row['timestamp']} | {row['action']} | {row['rule_title']}"
            for _, row in display_logs_df.iterrows()
        ]
        selected_record = st.selectbox("Select a record", options, index=0)
        selected_case_no = int(selected_record.split("|")[0].strip())
        record = display_logs_df[display_logs_df["case_no"] == selected_case_no].iloc[0]

        left, right = st.columns(2)
        with left:
            st.markdown(f"**Case Number:** {record['case_no']}")
            st.markdown(f"**Timestamp:** {record['timestamp']}")
            st.markdown(f"**User:** {record['user']}")
            st.markdown(f"**Role:** {record['role']}")
            st.markdown(f"**Role Adjustment:** {record['role_adjustment']}")
            st.markdown(f"**Source:** {record['source']}")
            st.markdown(f"**Site Mode:** {record['site_mode']}")
            st.markdown(f"**Site Adjustment:** {record['site_adjustment']}")
            st.markdown(f"**Action:** {record['action']}")
            st.markdown(f"**Reason:** {record['reason']}")
            st.markdown(f"**Message:** {record['message']}")
        with right:
            st.markdown(f"**Matched Rule ID:** {record['rule_id']}")
            st.markdown(f"**Matched Rule Title:** {record['rule_title']}")
            st.markdown(f"**Severity:** {record['severity']}")
            st.markdown(f"**Semantic Score:** {round(float(record['semantic_score']), 3)}")
            st.markdown(f"**Context Score:** {int(record.get('context_score', 0))}")
            st.markdown(f"**Fuzzy Score:** {int(record.get('fuzzy_score', 0))}")
            st.markdown(f"**Pattern Score:** {int(record['pattern_score'])}")
            st.markdown(f"**Risk Score:** {int(record['risk_score'])}")

        st.markdown("**Prompt Text**")
        st.code(record["text"] if pd.notna(record["text"]) else "", language="text")

        if isinstance(record["pattern_hits"], list) and record["pattern_hits"]:
            st.markdown("**Pattern Hits**")
            st.json(record["pattern_hits"])

        if bool(record["redaction_available"]) and record["redacted_text"]:
            st.markdown("**Suggested Redacted Version**")
            st.code(record["redacted_text"], language="text")

with tab4:
    from engine.user_context import get_active_user, set_active_user

    st.subheader("Role Management")

    user_roles = load_user_roles()
    existing_users = sorted(set(df["user"].dropna().tolist()) | set(user_roles.keys()))
    if not existing_users:
        existing_users = ["boss"]

    st.markdown("### Assign Role")

    col1, col2 = st.columns([2, 2])

    with col1:
        selected_user = st.selectbox("Select User", existing_users)

    with col2:
        current_role = user_roles.get(selected_user, "employee")
        selected_role = st.selectbox(
            "Assign Role",
            VALID_ROLES,
            index=VALID_ROLES.index(current_role) if current_role in VALID_ROLES else 0
        )

    if st.button("Save Role Assignment"):
        try:
            set_user_role(selected_user, selected_role)
            st.success(f"Role for '{selected_user}' updated to '{selected_role}'.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save role: {e}")

    st.markdown("---")
    st.markdown("### Active Test User")

    current_active_user = get_active_user()
    active_user = st.selectbox(
        "Select Active User For Extension",
        existing_users,
        index=existing_users.index(current_active_user) if current_active_user in existing_users else 0
    )

    if st.button("Set Active User"):
        try:
            set_active_user(active_user)
            st.success(f"Active user set to '{active_user}'.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to set active user: {e}")

    st.markdown("---")
    st.markdown(f"**Current Active User:** `{get_active_user()}`")

    st.markdown("### Current Role Assignments")
    role_df = pd.DataFrame([{"user": user, "role": role} for user, role in load_user_roles().items()])
    if not role_df.empty:
        st.dataframe(role_df, width="stretch", hide_index=True)
        
with tab5:
    st.subheader("Site Management")

    site_policies = load_site_policies()

    if not site_policies:
        st.info("No site policies found. Add one below.")
        site_policies = []

    domains = [p.get("domain", "") for p in site_policies if p.get("domain")]

    st.markdown("### Edit Existing Site")

    selected_domain = st.selectbox(
        "Select Site",
        [""] + domains
    )

    selected_policy = next((p for p in site_policies if p.get("domain") == selected_domain), None)

    col1, col2, col3 = st.columns(3)

    with col1:
        domain_input = st.text_input(
            "Domain",
            value=selected_policy.get("domain", "") if selected_policy else "",
            disabled=bool(selected_policy)  # prevent editing domain itself
        )

    with col2:
        label_input = st.text_input(
            "Label",
            value=selected_policy.get("label", "") if selected_policy else ""
        )

    with col3:
        mode_input = st.selectbox(
            "Mode",
            VALID_MODES,
            index=VALID_MODES.index(selected_policy.get("mode", "monitor"))
            if selected_policy else VALID_MODES.index("monitor")
        )

    enabled_input = st.checkbox(
        "Enabled",
        value=selected_policy.get("enabled", True) if selected_policy else True
    )

    if st.button("Update Site Policy"):
        if domain_input.strip():
            upsert_site_policy(
                domain_input.strip(),
                label_input.strip() or domain_input.strip(),
                mode_input,
                enabled_input
            )
            st.success(f"Updated policy for {domain_input}")
            st.rerun()
        else:
            st.error("Domain cannot be empty.")

    st.markdown("---")

    st.markdown("### Add New Site")

    col1, col2, col3 = st.columns(3)

    with col1:
        new_domain = st.text_input("New Domain", key="new_domain")

    with col2:
        new_label = st.text_input("New Label", key="new_label")

    with col3:
        new_mode = st.selectbox("Mode", VALID_MODES, key="new_mode")

    new_enabled = st.checkbox("Enabled", value=True, key="new_enabled")

    if st.button("Add Site Policy"):
        if new_domain.strip():
            upsert_site_policy(
                new_domain.strip(),
                new_label.strip() or new_domain.strip(),
                new_mode,
                new_enabled
            )
            st.success(f"Added site {new_domain}")
            st.rerun()
        else:
            st.error("Domain cannot be empty.")

    st.markdown("---")

    st.markdown("### Existing Site Policies")

    if site_policies:
        site_df = pd.DataFrame(site_policies)
        st.dataframe(site_df, width="stretch", hide_index=True)

        delete_domain = st.selectbox(
            "Select domain to delete",
            [""] + domains
        )

        if st.button("Delete Site Policy"):
            if delete_domain:
                delete_site_policy(delete_domain)
                st.success(f"Deleted {delete_domain}")
                st.rerun()