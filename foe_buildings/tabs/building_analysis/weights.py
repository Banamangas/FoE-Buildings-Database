import hashlib
import json

import pandas as pd
import streamlit as st

from foe_buildings import config
from foe_buildings import i18n as translations


def _weights_state_hash(
    user_weights: dict,
    user_context: dict,
    user_boosts: dict,
    scoring_mode: str = "classic",
) -> str:
    """Return a stable hash of the current weights/context/boosts/mode state."""
    data = {
        "w": {k: v for k, v in sorted(user_weights.items()) if v != 0},
        "c": {k: v for k, v in sorted(user_context.items())},
        "b": {k: v for k, v in sorted(user_boosts.items())},
        "m": scoring_mode,
    }
    return hashlib.md5(json.dumps(data).encode()).hexdigest()


def render_weights_subtab(
    df_original: pd.DataFrame,
    user_weights: dict,
    user_context: dict,
    user_boosts: dict,
    lang_code: str,
) -> None:
    # Apply any pending profile import BEFORE widgets are instantiated.
    # We cannot set widget state keys after a widget is rendered, so the import
    # block stores data here and we apply it on the next rerun at this point.
    _pending = st.session_state.pop("_pending_profile_import", None)
    if _pending is not None:
        for k, v in _pending.get("weights", {}).items():
            st.session_state[config.SessionKeys.USER_WEIGHTS][k] = float(v)
            st.session_state[f"weight_{k}"] = float(v)
        for k, v in _pending.get("context", {}).items():
            st.session_state[config.SessionKeys.USER_CONTEXT][k] = float(v)
            st.session_state[f"context_{k}"] = float(v)
        for k, v in _pending.get("boosts", {}).items():
            st.session_state[config.SessionKeys.USER_BOOSTS][k] = float(v)
            st.session_state[f"boost_{k}"] = float(v)

    # --- Weighting Inputs ---
    st.header(translations.get_text("efficiency_weights", lang_code))
    st.markdown(translations.get_text("efficiency_help_direct", lang_code))
    st.info(translations.get_text("reminder_city_context", lang_code))
    st.markdown("---")

    # --- Scoring Mode Toggle ---
    scoring_mode = st.radio(
        translations.get_text("scoring_mode_label", lang_code),
        options=["classic", "normalised"],
        format_func=lambda m: translations.get_text(f"scoring_mode_{m}", lang_code),
        index=0
        if st.session_state.get(config.SessionKeys.SCORING_MODE, "classic") == "classic"
        else 1,
        horizontal=True,
        key="scoring_mode_radio",
        help=translations.get_text("scoring_mode_help", lang_code),
    )
    st.session_state[config.SessionKeys.SCORING_MODE] = scoring_mode

    # --- Scoring Mode Explanation ---
    explanation_key = (
        "scoring_explanation_normalised_body"
        if scoring_mode == "normalised"
        else "scoring_explanation_classic_body"
    )
    with st.expander(
        translations.get_text("scoring_explanation_title", lang_code),
        expanded=False,
    ):
        st.markdown(translations.get_text(explanation_key, lang_code))
    st.markdown("---")

    # --- Weight Presets ---
    preset_keys = list(config.WEIGHT_PRESETS.keys())
    preset_col1, preset_col2 = st.columns([1, 3])
    st.markdown(
        f"<div style='padding-top:6px;font-size:1.2rem;font-weight:600'>{translations.get_text('weight_presets_label', lang_code)}</div>",
        unsafe_allow_html=True,
    )
    with preset_col1:
        selected_preset_key = st.selectbox(
            translations.get_text("weight_presets_label", lang_code),
            options=[None] + preset_keys,
            format_func=lambda k: ""
            if k is None
            else translations.get_text(f"weight_preset_{k}", lang_code),
            label_visibility="collapsed",
            help=translations.get_text("weight_presets_help", lang_code),
            key="weight_preset_selector",
        )
    with preset_col2:
        if st.button(
            translations.get_text("load_preset", lang_code),
            disabled=selected_preset_key is None,
        ):
            st.session_state["_pending_preset_load"] = config.WEIGHT_PRESETS[
                selected_preset_key
            ]
            st.rerun()
    st.markdown("---")

    # Create two columns for better layout
    left_col, right_col = st.columns(2)

    # Split the column groups between the two columns
    column_groups_list = list(config.COLUMN_GROUPS.items())
    mid_point = len(column_groups_list) // 2

    for col, groups in [
        (left_col, column_groups_list[:mid_point]),
        (right_col, column_groups_list[mid_point:]),
    ]:
        with col:
            for group_key, group_info in groups:
                # Find weightable columns within this group that exist in the data
                cols_in_group = group_info["columns"]
                inputs_to_create = []
                for col_name in cols_in_group:
                    # Check if the column exists in the loaded data
                    if (
                        col_name in df_original.columns
                        and col_name in config.WEIGHTABLE_COLUMNS
                    ):
                        # Check if the column is numeric before allowing weighting
                        if pd.api.types.is_numeric_dtype(df_original[col_name]):
                            inputs_to_create.append(col_name)

                if inputs_to_create:  # Only show expander if there are inputs to create
                    with st.expander(
                        translations.get_text(group_key, lang_code),
                        expanded=False,
                    ):
                        for col_name in inputs_to_create:
                            # Skip boost metrics as they're now integrated into base metrics
                            if col_name in config.BOOST_TO_BASE_MAPPING:
                                continue

                            help_text = f"Points per {translations.translate_column(col_name, lang_code).lower()}"

                            weight_value = st.number_input(
                                label=f"1 {translations.translate_column(col_name, lang_code)} = ___ Points",
                                help=help_text,
                                value=user_weights.get(col_name, 0.0),
                                min_value=0.0,
                                step=0.05,
                                format="%.2f",
                                key=f"weight_{col_name}",
                            )
                            user_weights[col_name] = weight_value
                            st.session_state[config.SessionKeys.USER_WEIGHTS][
                                col_name
                            ] = weight_value
    st.markdown("---")
    # --- User Context Section ---
    st.header(translations.get_text("user_context", lang_code))
    st.markdown(translations.get_text("user_context_help", lang_code))

    # Base Production Section
    st.subheader(translations.get_text("base_production_section", lang_code))

    # Create two columns for base production inputs
    ctx_left_col, ctx_right_col = st.columns(2)

    context_fields = list(config.USER_CONTEXT_FIELDS.items())
    mid_point = len(context_fields) // 2

    for col, fields in [
        (ctx_left_col, context_fields[:mid_point]),
        (ctx_right_col, context_fields[mid_point:]),
    ]:
        with col:
            for field_key, field_config in fields:
                context_value = st.number_input(
                    label=translations.get_text(
                        str(field_config["label_key"]), lang_code
                    ),
                    help=translations.get_text(
                        str(field_config["help_key"]), lang_code
                    ),
                    value=user_context.get(
                        field_key, float(str(field_config["default"]))
                    ),
                    min_value=0.0,
                    step=1.0
                    if field_key
                    in [
                        "fp_daily_production",
                        "medal_production",
                        "special_goods_production",
                        "guild_goods_production",
                    ]
                    else 100.0,
                    key=f"context_{field_key}",
                )
                user_context[field_key] = context_value
                st.session_state[config.SessionKeys.USER_CONTEXT][field_key] = (
                    context_value
                )

    # Current Boosts Section
    st.subheader(translations.get_text("current_boosts_section", lang_code))

    # Create two columns for boost inputs
    boost_left_col, boost_right_col = st.columns(2)

    boost_fields = list(config.USER_BOOST_FIELDS.items())
    boost_mid_point = len(boost_fields) // 2

    for col, fields in [
        (boost_left_col, boost_fields[:boost_mid_point]),
        (boost_right_col, boost_fields[boost_mid_point:]),
    ]:
        with col:
            for field_key, field_config in fields:
                boost_value = st.number_input(
                    label=translations.get_text(
                        str(field_config["label_key"]), lang_code
                    ),
                    help=translations.get_text(
                        str(field_config["help_key"]), lang_code
                    ),
                    value=user_boosts.get(
                        field_key, float(str(field_config["default"]))
                    ),
                    min_value=0.0,
                    max_value=1000.0,
                    step=1.0,
                    format="%.1f",
                    key=f"boost_{field_key}",
                )
                user_boosts[field_key] = boost_value
                st.session_state[config.SessionKeys.USER_BOOSTS][field_key] = (
                    boost_value
                )

    st.markdown("---")
    st.subheader(translations.get_text("weight_profile", lang_code))

    profile_col1, profile_col2 = st.columns(2)

    with profile_col1:
        # Export
        profile_data = {
            "weights": st.session_state[config.SessionKeys.USER_WEIGHTS],
            "context": st.session_state[config.SessionKeys.USER_CONTEXT],
            "boosts": st.session_state[config.SessionKeys.USER_BOOSTS],
        }
        profile_json = json.dumps(profile_data, indent=2)
        st.download_button(
            label=translations.get_text("export_profile", lang_code),
            data=profile_json,
            file_name="foe_weight_profile.json",
            mime="application/json",
            help=translations.get_text("export_profile_help", lang_code),
        )

    with profile_col2:
        # Import — use a counter key so the widget resets after a successful import
        if "profile_uploader_key" not in st.session_state:
            st.session_state["profile_uploader_key"] = 0
        uploaded = st.file_uploader(
            translations.get_text("import_profile", lang_code),
            type=["json"],
            help=translations.get_text("import_profile_help", lang_code),
            key=f"profile_uploader_{st.session_state['profile_uploader_key']}",
        )
        if uploaded is not None:
            try:
                imported = json.load(uploaded)
                # Stage the import — widget keys cannot be set after instantiation,
                # so store here and apply at the top of the subtab on the next rerun.
                st.session_state["_pending_profile_import"] = imported
                st.session_state["profile_uploader_key"] += 1
                st.rerun()
            except Exception as e:
                st.error(
                    translations.get_text("profile_import_error", lang_code) + f": {e}"
                )
