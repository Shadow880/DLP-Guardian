import json
from pathlib import Path

import pandas as pd
import streamlit as st

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

                row = {
                    "timestamp": obj.get("timestamp", ""),
                    "user": obj.get("user", "unknown"),
                    "source": obj.get("source", "unknown"),
                    "channel": obj.get("channel", "unknown"),
                    "text": obj.get("text", ""),
                    "action": decision.get("action", ""),
                    "allowed": decision.get("allowed", ""),
                    "reason": decision.get("reason", ""),
                    "message": decision.get("message", ""),
                    "rule_id": matched_rule.get("id", ""),
                    "rule_title": matched_rule.get("title", ""),
                    "rule_type": matched_rule.get("type", ""),
                    "severity": matched_rule.get("severity", ""),
                    "similarity": matched_rule.get("similarity", ""),
                    "detection_source": decision.get("detection_source", ""),
                    "pattern_hits": decision.get("pattern_hits", []),
                }
                rows.append(row)

            except Exception:
                continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)

    total = len(df)
    df.insert(0, "case_no", list(range(total, 0, -1)))
    return df


try:
    st.caption(f"Reading logs from: {LOG_PATH}")
    df = load_logs()

    if df.empty:
        st.warning("No log data found yet. Run a few prompt checks first.")
        st.stop()

    st.sidebar.header("Filters")

    action_options = sorted([x for x in df["action"].dropna().unique().tolist() if x != ""])
    selected_actions = st.sidebar.multiselect("Action", action_options, default=action_options)

    severity_options = sorted([x for x in df["severity"].dropna().unique().tolist() if x != ""])
    selected_severities = st.sidebar.multiselect("Severity", severity_options, default=severity_options)

    source_options = sorted([x for x in df["source"].dropna().unique().tolist() if x != ""])
    selected_sources = st.sidebar.multiselect("Source", source_options, default=source_options)

    search_text = st.sidebar.text_input("Search prompt text")

    filtered_df = df.copy()

    if selected_actions:
        filtered_df = filtered_df[filtered_df["action"].isin(selected_actions)]

    if selected_severities:
        filtered_df = filtered_df[filtered_df["severity"].isin(selected_severities)]

    if selected_sources:
        filtered_df = filtered_df[filtered_df["source"].isin(selected_sources)]

    if search_text.strip():
        filtered_df = filtered_df[
            filtered_df["text"].fillna("").str.contains(search_text, case=False, na=False)
        ]

    total_checks = len(filtered_df)
    allow_count = int((filtered_df["action"] == "allow").sum())
    warn_count = int((filtered_df["action"] == "warn").sum())
    block_count = int((filtered_df["action"] == "block").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Checks", total_checks)
    c2.metric("Allowed", allow_count)
    c3.metric("Warnings", warn_count)
    c4.metric("Blocked", block_count)

    st.markdown("---")

    display_df = filtered_df.copy()

    display_df["text_preview"] = display_df["text"].fillna("").apply(
        lambda x: x[:160] + "..." if len(x) > 160 else x
    )

    display_df["pattern_hits_display"] = display_df["pattern_hits"].apply(
        lambda x: ", ".join([item.get("type", "") for item in x]) if isinstance(x, list) else ""
    )

    display_df["similarity"] = display_df["similarity"].apply(
        lambda x: round(float(x), 3) if str(x).strip() != "" else ""
    )

    table_df = display_df[
        [
            "case_no",
            "timestamp",
            "action",
            "severity",
            "rule_title",
            "similarity",
            "source",
            "detection_source",
            "pattern_hits_display",
            "text_preview",
        ]
    ].rename(
        columns={
            "case_no": "case",
            "rule_title": "matched_rule",
            "pattern_hits_display": "pattern_hits",
        }
    )

    st.subheader("Recent Decisions")
    st.dataframe(
        table_df,
        use_container_width=True,
        height=460,
        column_config={
            "case": st.column_config.NumberColumn("Case", width="small"),
            "timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
            "action": st.column_config.TextColumn("Action", width="small"),
            "severity": st.column_config.TextColumn("Severity", width="small"),
            "matched_rule": st.column_config.TextColumn("Matched Rule", width="large"),
            "similarity": st.column_config.NumberColumn("Similarity", format="%.3f", width="small"),
            "source": st.column_config.TextColumn("Source", width="medium"),
            "detection_source": st.column_config.TextColumn("Detection", width="small"),
            "pattern_hits": st.column_config.TextColumn("Pattern Hits", width="medium"),
            "text_preview": st.column_config.TextColumn("Prompt Preview", width="large"),
        },
        hide_index=True,
    )

    st.markdown("---")

    st.subheader("Detailed Record View")

    record_options = [
        f"{row['case_no']} | {row['timestamp']} | {row['action']} | {row['rule_title']}"
        for _, row in filtered_df.iterrows()
    ]

    selected_record = st.selectbox("Select a record", record_options)

    if selected_record:
        selected_case_no = int(selected_record.split("|")[0].strip())
        record = filtered_df[filtered_df["case_no"] == selected_case_no].iloc[0]

        left, right = st.columns(2)

        with left:
            st.markdown(f"**Case Number:** {record['case_no']}")
            st.markdown(f"**Timestamp:** {record['timestamp']}")
            st.markdown(f"**Action:** {record['action']}")
            st.markdown(f"**Allowed:** {record['allowed']}")
            st.markdown(f"**Reason:** {record['reason']}")
            st.markdown(f"**Detection Source:** {record['detection_source']}")
            st.markdown(f"**Source:** {record['source']}")
            st.markdown(f"**Channel:** {record['channel']}")
            st.markdown(f"**User:** {record['user']}")

        with right:
            st.markdown(f"**Matched Rule ID:** {record['rule_id']}")
            st.markdown(f"**Matched Rule Title:** {record['rule_title']}")
            st.markdown(f"**Rule Type:** {record['rule_type']}")
            st.markdown(f"**Severity:** {record['severity']}")
            st.markdown(f"**Similarity:** {record['similarity']}")

        st.markdown("**Prompt Text**")
        st.code(record["text"] if pd.notna(record["text"]) else "", language="text")

        st.markdown("**Message**")
        st.info(record["message"] if pd.notna(record["message"]) else "")

        if isinstance(record["pattern_hits"], list) and record["pattern_hits"]:
            st.markdown("**Pattern Hits**")
            st.json(record["pattern_hits"])

except Exception as e:
    st.error(f"Dashboard error: {e}")