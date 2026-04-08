from typing import Dict, Optional
import pandas as pd

# Import configurations and logger
from config import (
    ADDITIVE_METRICS,
    BOOST_TO_BASE_MAPPING,
    USER_CONTEXT_FIELDS,
    USER_BOOST_FIELDS,
    PER_SQUARE_EXCLUDED_COLUMNS,
    C1_SCORE_MULTIPLIER,
    logger,
    COL_ERA,
    COL_SIZE,
    COL_TOTAL_SCORE,
    COL_WEIGHTED_EFFICIENCY,
)


# --- Per-Square Helper ---
def apply_per_square(df: pd.DataFrame, divisor_series: pd.Series) -> pd.DataFrame:
    """Divide all numeric, non-excluded columns by the per-square divisor.

    Args:
        df: DataFrame to modify in-place (copy first if needed).
        divisor_series: Series of square counts, already reindexed to df's index
                        and with zeros/NA replaced by 1.

    Returns:
        The modified DataFrame (same object).
    """
    numeric_cols = [
        col
        for col in df.columns
        if col not in PER_SQUARE_EXCLUDED_COLUMNS
        and pd.api.types.is_numeric_dtype(df[col])
    ]
    for col in numeric_cols:
        df[col] = (df[col] / divisor_series).round(8)
    return df


# --- Era Statistics Calculation --- (Cached in calling function)
# @st.cache_data # Cache decorator moved to the calling function in app.py
def calculate_era_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate per-era min/max statistics for all weightable columns.

    Used by the heatmap renderer to normalise column values to [0, 1] within
    each era. Results are cached by the caller (app.py:cached_calculate_era_stats).

    Args:
        df: Full building DataFrame with an 'Era' column.

    Returns:
        DataFrame with a MultiIndex on columns: (metric, 'min'|'max'), indexed by era.
        Returns an empty DataFrame if df is empty or lacks weightable columns.
    """
    logger.info("Calculating min/max statistics per era...")
    if df.empty or COL_ERA not in df.columns:
        logger.warning(
            "Cannot calculate era stats: DataFrame is empty or missing 'Era' column."
        )
        return pd.DataFrame()  # Return empty DataFrame if no data

    # Ensure additive metrics exist in the DataFrame (covers all scoring columns)
    cols_to_agg = [col for col in ADDITIVE_METRICS if col in df.columns]
    if not cols_to_agg:
        logger.warning(
            "Cannot calculate era stats: No weightable columns found in DataFrame."
        )
        return pd.DataFrame()

    try:
        # observed=False retains all era categories even when some have no buildings
        # after filtering, preventing KeyError in the heatmap normalisation lookup.
        stats = df.groupby(COL_ERA, observed=False)[cols_to_agg].agg(["min", "max"])

        logger.info("Era statistics (min/max) calculation complete.")
        return stats
    except Exception as e:
        logger.error(f"Error calculating era statistics: {e}", exc_info=True)
        return pd.DataFrame()  # Return empty on error


# --- Direct Weighted Sum Calculation ---
def _apply_multiplier_boost(base_value: float, boost_pct: float) -> float:
    """Return base_value boosted by boost_pct percent. Returns base_value unchanged if boost_pct <= 0."""
    if boost_pct <= 0:
        return base_value
    return base_value * (1 + boost_pct / 100)


def _compute_combined_boosts(building_row: pd.Series, user_boosts: dict) -> dict:
    """Return combined boost % dict (user city boost + building's own boost) for each resource type."""
    user_fp_boost = user_boosts.get("current_fp_boost", 0)
    building_fp_boost = building_row.get("FP boost", 0)

    user_goods_boost = user_boosts.get("current_goods_boost", 0)
    building_goods_boost = building_row.get("Goods Boost", 0)

    user_guild_goods_boost = user_boosts.get("current_guild_goods_boost", 0)
    building_guild_goods_boost = building_row.get("Guild Goods Production %", 0)

    user_special_goods_boost = user_boosts.get("current_special_goods_boost", 0)
    building_special_goods_boost = building_row.get("Special Goods Production %", 0)

    return {
        "fp": user_fp_boost + building_fp_boost,
        "goods": user_goods_boost + building_goods_boost,
        "guild_goods": user_guild_goods_boost + building_guild_goods_boost,
        "special_goods": user_special_goods_boost + building_special_goods_boost,
        # Keep individual user/building components for debug logging
        "_user_fp_boost": user_fp_boost,
        "_building_fp_boost": building_fp_boost,
        "_user_goods_boost": user_goods_boost,
        "_building_goods_boost": building_goods_boost,
        "_user_guild_goods_boost": user_guild_goods_boost,
        "_building_guild_goods_boost": building_guild_goods_boost,
        "_user_special_goods_boost": user_special_goods_boost,
        "_building_special_goods_boost": building_special_goods_boost,
    }


def _apply_production_boosts(
    enhanced_row: pd.Series, original_base_values: dict, combined_boosts: dict
) -> pd.Series:
    """Apply combined boost percentages to the base production values and return the updated row."""
    # Apply FP boost
    if "forge_points" in enhanced_row:
        enhanced_row["forge_points"] = _apply_multiplier_boost(
            original_base_values["forge_points"], combined_boosts["fp"]
        )
        if combined_boosts["fp"] > 0:
            logger.debug(
                f"Applied combined FP boost ({combined_boosts['fp']}% = "
                f"{combined_boosts['_user_fp_boost']}% user + {combined_boosts['_building_fp_boost']}% building) "
                f"to base FP production: {original_base_values['forge_points']:.1f} -> {enhanced_row['forge_points']:.1f}"
            )

    # Apply Goods boost
    for goods_col in ["goods", "prev_age_goods", "next_age_goods"]:
        if goods_col in enhanced_row:
            enhanced_row[goods_col] = _apply_multiplier_boost(
                original_base_values[goods_col], combined_boosts["goods"]
            )
            if combined_boosts["goods"] > 0:
                logger.debug(
                    f"Applied combined Goods boost ({combined_boosts['goods']}% = "
                    f"{combined_boosts['_user_goods_boost']}% user + {combined_boosts['_building_goods_boost']}% building) "
                    f"to base {goods_col} production: {original_base_values[goods_col]:.1f} -> {enhanced_row[goods_col]:.1f}"
                )

    # Apply Guild Goods boost
    if "guild_goods" in enhanced_row:
        enhanced_row["guild_goods"] = _apply_multiplier_boost(
            original_base_values["guild_goods"], combined_boosts["guild_goods"]
        )
        if combined_boosts["guild_goods"] > 0:
            logger.debug(
                f"Applied combined Guild Goods boost ({combined_boosts['guild_goods']}% = "
                f"{combined_boosts['_user_guild_goods_boost']}% user + {combined_boosts['_building_guild_goods_boost']}% building) "
                f"to base guild goods production: {original_base_values['guild_goods']:.1f} -> {enhanced_row['guild_goods']:.1f}"
            )

    # Apply Special Goods boost
    if "special_goods" in enhanced_row:
        enhanced_row["special_goods"] = _apply_multiplier_boost(
            original_base_values["special_goods"], combined_boosts["special_goods"]
        )
        if combined_boosts["special_goods"] > 0:
            logger.debug(
                f"Applied combined Special Goods boost ({combined_boosts['special_goods']}% = "
                f"{combined_boosts['_user_special_goods_boost']}% user + {combined_boosts['_building_special_goods_boost']}% building) "
                f"to base special goods production: {original_base_values['special_goods']:.1f} -> {enhanced_row['special_goods']:.1f}"
            )

    return enhanced_row


def _compute_true_base_context(user_context: dict, user_boosts: dict) -> dict:
    """Reverse-engineer the true (un-boosted) base production from user's current reported production."""
    true_base_context = {}

    # FP: true_base = current_production / (1 + current_boost/100)
    if "current_fp_boost" in user_boosts and user_boosts["current_fp_boost"] > 0:
        boost_multiplier = 1 + (user_boosts["current_fp_boost"] / 100)
        true_base_context["fp_daily_production"] = (
            user_context.get("fp_daily_production", 0) / boost_multiplier
        )
    else:
        true_base_context["fp_daily_production"] = user_context.get(
            "fp_daily_production", 0
        )

    # Goods: Calculate true base for each goods type
    if "current_goods_boost" in user_boosts and user_boosts["current_goods_boost"] > 0:
        boost_multiplier = 1 + (user_boosts["current_goods_boost"] / 100)
        true_base_context["goods_current_production"] = (
            user_context.get("goods_current_production", 0) / boost_multiplier
        )
        true_base_context["goods_previous_production"] = (
            user_context.get("goods_previous_production", 0) / boost_multiplier
        )
        true_base_context["goods_next_production"] = (
            user_context.get("goods_next_production", 0) / boost_multiplier
        )
    else:
        true_base_context["goods_current_production"] = user_context.get(
            "goods_current_production", 0
        )
        true_base_context["goods_previous_production"] = user_context.get(
            "goods_previous_production", 0
        )
        true_base_context["goods_next_production"] = user_context.get(
            "goods_next_production", 0
        )

    # Guild Goods
    if (
        "current_guild_goods_boost" in user_boosts
        and user_boosts["current_guild_goods_boost"] > 0
    ):
        boost_multiplier = 1 + (user_boosts["current_guild_goods_boost"] / 100)
        true_base_context["guild_goods_production"] = (
            user_context.get("guild_goods_production", 0) / boost_multiplier
        )
    else:
        true_base_context["guild_goods_production"] = user_context.get(
            "guild_goods_production", 0
        )

    # Special Goods
    if (
        "current_special_goods_boost" in user_boosts
        and user_boosts["current_special_goods_boost"] > 0
    ):
        boost_multiplier = 1 + (user_boosts["current_special_goods_boost"] / 100)
        true_base_context["special_goods_production"] = (
            user_context.get("special_goods_production", 0) / boost_multiplier
        )
    else:
        true_base_context["special_goods_production"] = user_context.get(
            "special_goods_production", 0
        )

    return true_base_context


def _apply_context_boosts(
    enhanced_row: pd.Series, building_row: pd.Series, true_base_context: dict
) -> pd.Series:
    """Convert the building's percentage boost columns into equivalent production units."""
    for boost_metric, base_metric_or_list in BOOST_TO_BASE_MAPPING.items():
        if boost_metric in building_row and building_row[boost_metric] > 0:
            boost_percentage = building_row[boost_metric]

            if boost_metric == "FP boost":
                context_key = "fp_daily_production"
                if context_key in true_base_context:
                    boost_equivalent = (
                        boost_percentage * true_base_context[context_key] / 100
                    )
                    current_base = enhanced_row.get(base_metric_or_list, 0)
                    enhanced_row[base_metric_or_list] = current_base + boost_equivalent
                    logger.debug(
                        f"Applied {boost_metric} ({boost_percentage}%) to {base_metric_or_list}: +{boost_equivalent:.1f} (true base: {true_base_context[context_key]:.1f})"
                    )

            elif boost_metric == "Goods Boost":
                # Goods Boost affects multiple goods types
                context_keys = [
                    "goods_current_production",
                    "goods_previous_production",
                    "goods_next_production",
                ]
                base_metric_names = ["goods", "prev_age_goods", "next_age_goods"]

                for context_key, base_metric in zip(context_keys, base_metric_names):
                    if (
                        context_key in true_base_context
                        and true_base_context[context_key] > 0
                    ):
                        boost_equivalent = (
                            boost_percentage * true_base_context[context_key] / 100
                        )
                        current_base = enhanced_row.get(base_metric, 0)
                        enhanced_row[base_metric] = current_base + boost_equivalent
                        logger.debug(
                            f"Applied {boost_metric} ({boost_percentage}%) to {base_metric}: +{boost_equivalent:.1f} (true base: {true_base_context[context_key]:.1f})"
                        )

            elif boost_metric == "Guild Goods Production %":
                context_key = "guild_goods_production"
                if context_key in true_base_context:
                    boost_equivalent = (
                        boost_percentage * true_base_context[context_key] / 100
                    )
                    current_base = enhanced_row.get(base_metric_or_list, 0)
                    enhanced_row[base_metric_or_list] = current_base + boost_equivalent
                    logger.debug(
                        f"Applied {boost_metric} ({boost_percentage}%) to {base_metric_or_list}: +{boost_equivalent:.1f} (true base: {true_base_context[context_key]:.1f})"
                    )

            elif boost_metric == "Special Goods Production %":
                context_key = "special_goods_production"
                if context_key in true_base_context:
                    boost_equivalent = (
                        boost_percentage * true_base_context[context_key] / 100
                    )
                    current_base = enhanced_row.get(base_metric_or_list, 0)
                    enhanced_row[base_metric_or_list] = current_base + boost_equivalent
                    logger.debug(
                        f"Applied {boost_metric} ({boost_percentage}%) to {base_metric_or_list}: +{boost_equivalent:.1f} (true base: {true_base_context[context_key]:.1f})"
                    )

    return enhanced_row


def apply_boosts_to_base_metrics(
    building_row: pd.Series,
    user_context: Dict[str, float],
    user_boosts: Dict[str, float],
    true_base_context: Optional[Dict[str, float]] = None,
) -> pd.Series:
    """Apply city boosts and building self-boosts to the building's base production values.

    Three-step pipeline (see CLAUDE.md § Boost Algorithm for rationale):
      1. Compute combined boost % = user city boost + building self-boost.
      2. Apply combined boost to the building's raw base production values.
      3. Convert building's *percentage-boost* columns (FP boost, Goods Boost, …) into
         equivalent production units by multiplying against the user's *true* (un-boosted)
         base production, which is reverse-engineered from their reported daily output.

    Args:
        building_row: Single row from the building DataFrame.
        user_context: Daily production figures entered by the user (e.g. fp_daily_production).
        user_boosts: Current city boost percentages (e.g. current_fp_boost).
        true_base_context: Pre-computed result of _compute_true_base_context(user_context,
            user_boosts). Pass this when calling in a loop to avoid recomputing it for
            every row — it only depends on user inputs, not on the building. If None,
            it is computed here (correct but wasteful in a loop).

    Returns:
        A copy of building_row with production columns adjusted to reflect all boosts.
    """
    # Create a copy to avoid modifying the original
    enhanced_row = building_row.copy()

    # Store original base production values
    original_base_values = {
        "forge_points": building_row.get("forge_points", 0),
        "goods": building_row.get("goods", 0),
        "prev_age_goods": building_row.get("prev_age_goods", 0),
        "next_age_goods": building_row.get("next_age_goods", 0),
        "guild_goods": building_row.get("guild_goods", 0),
        "special_goods": building_row.get("special_goods", 0),
    }

    # STEP 1: Compute combined boost percentages (user city boost + building self-boost)
    combined_boosts = _compute_combined_boosts(building_row, user_boosts)

    # Apply combined boosts to original base values
    enhanced_row = _apply_production_boosts(
        enhanced_row, original_base_values, combined_boosts
    )

    # STEP 2: True base production — reverse-engineer from user's boosted daily output.
    # This is the same for every building; callers in a loop should pass it pre-computed.
    if true_base_context is None:
        true_base_context = _compute_true_base_context(user_context, user_boosts)

    # STEP 3: Apply building boosts to user context (for boost buildings)
    # This handles boost buildings (buildings that provide percentage boosts to the user's daily production)
    enhanced_row = _apply_context_boosts(enhanced_row, building_row, true_base_context)

    return enhanced_row


def calculate_direct_weighted_efficiency(
    df: pd.DataFrame,
    user_weights: Dict[str, float],
    user_context: Dict[str, float],
    user_boosts: Optional[Dict[str, float]] = None,
    era_stats_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Calculate weighted efficiency using direct weighted sum with integrated boosts.

    When era_stats_df is provided (non-empty), C1 per-era max normalisation is applied:
    each metric value is divided by the era's maximum before weighting, then multiplied
    by C1_SCORE_MULTIPLIER (100) for display readability (e.g. 0.0278 → 2.78).

    When era_stats_df is None, classic mode: raw values are used unchanged (backward
    compatible with all existing call sites).
    """
    logger.info(f"Calculating direct weighted efficiency for {len(df)} buildings")

    if df.empty:
        logger.warning(
            "Empty dataframe provided to calculate_direct_weighted_efficiency"
        )
        return df

    # Default empty user_boosts if not provided
    if user_boosts is None:
        user_boosts = {}

    # Initialize columns
    df[COL_TOTAL_SCORE] = 0.0
    df[COL_WEIGHTED_EFFICIENCY] = 0.0

    # Check if any weights are set
    any_weight_set = any(w > 0 for w in user_weights.values())
    if not any_weight_set:
        logger.info("No weights set, returning zero scores")
        return df

    try:
        # Pre-compute once: true_base_context only depends on user inputs, not on any building row.
        true_base_context = _compute_true_base_context(user_context, user_boosts)

        for idx, building_row in df.iterrows():
            # Apply boosts to base metrics first (pass pre-computed true_base_context to avoid
            # recomputing it for every building — it is the same for all rows in this call).
            enhanced_row = apply_boosts_to_base_metrics(
                building_row, user_context, user_boosts, true_base_context
            )

            # Pre-resolve era for C1 normalisation (None in classic mode)
            building_era = (
                building_row.get(COL_ERA)
                if (era_stats_df is not None and not era_stats_df.empty)
                else None
            )
            total_score = 0.0

            # Process all additive metrics (now including boost-enhanced values)
            for metric in ADDITIVE_METRICS:
                if metric in enhanced_row and metric in user_weights:
                    weight = user_weights.get(metric, 0)
                    if weight > 0 and pd.notna(enhanced_row[metric]):
                        value = float(enhanced_row[metric])

                        # C1: normalise by era max, then scale for display readability
                        if building_era is not None and era_stats_df is not None:
                            try:
                                era_max = era_stats_df.loc[
                                    building_era, (metric, "max")
                                ]
                                if pd.notna(era_max) and era_max > 0:
                                    value = (value / era_max) * C1_SCORE_MULTIPLIER
                                else:
                                    value = 0.0
                            except KeyError:
                                pass  # metric or era not in stats — use raw value

                        contribution = value * weight
                        total_score += contribution
                        logger.debug(
                            f"Building {idx}, {metric}: raw={enhanced_row[metric]:.4f}"
                            + (
                                f", norm×{C1_SCORE_MULTIPLIER}={value:.4f}"
                                if building_era is not None
                                else ""
                            )
                            + f" * {weight} = {contribution:.4f}"
                        )

            # Set total score
            decimal_places = (
                4 if (era_stats_df is not None and not era_stats_df.empty) else 1
            )
            df.at[idx, COL_TOTAL_SCORE] = round(total_score, decimal_places)

            # Calculate efficiency (score per tile)
            building_size = building_row.get(COL_SIZE, 1)
            if building_size > 0:
                efficiency = total_score / building_size
                df.at[idx, COL_WEIGHTED_EFFICIENCY] = round(efficiency, decimal_places)
            else:
                df.at[idx, COL_WEIGHTED_EFFICIENCY] = 0.0

        logger.info("Direct weighted efficiency calculation complete")

    except Exception as e:
        logger.error(
            f"Error in direct weighted efficiency calculation: {e}", exc_info=True
        )
        df[COL_TOTAL_SCORE] = 0.0
        df[COL_WEIGHTED_EFFICIENCY] = 0.0

    return df


# --- Legacy function for backward compatibility ---
def calculate_weighted_efficiency(
    df: pd.DataFrame,
    user_weights: Dict[str, float],
    era_stats_df: pd.DataFrame,
    df_original: pd.DataFrame,
    selected_translated_era: str,
    lang_code: str,
    user_context: Optional[Dict[str, float]] = None,
    user_boosts: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Legacy wrapper that calls the new direct weighted efficiency calculation."""
    if user_context is None:
        # Use default context if none provided
        user_context = {
            key: field_config["default"]
            for key, field_config in USER_CONTEXT_FIELDS.items()
        }

    if user_boosts is None:
        user_boosts = {
            key: field_config["default"]
            for key, field_config in USER_BOOST_FIELDS.items()
        }

    return calculate_direct_weighted_efficiency(
        df, user_weights, user_context, user_boosts
    )
