# Chungnam Synthetic Scenario Dataset – Modeling Guide

## Files
- `chungnam_synthetic_scenarios_490.csv`: full synthetic scenario dataset
- `chungnam_scenarios_train.csv`: train split
- `chungnam_scenarios_valid.csv`: validation split
- `chungnam_scenarios_test.csv`: test split
- `chungnam_feature_roles.csv`: column-by-column feature/target guide

## Split summary
- Train: 343 rows
- Validation: 70 rows
- Test: 77 rows

### `next_scene` class balance
- Train: {'cafe_rest': 49, 'go_home': 49, 'indoor_backup': 49, 'indoor_visit': 49, 'meal': 49, 'short_walk': 49, 'sunset_finish': 49}
- Validation: {'cafe_rest': 10, 'go_home': 10, 'indoor_backup': 10, 'indoor_visit': 10, 'meal': 10, 'short_walk': 10, 'sunset_finish': 10}
- Test: {'cafe_rest': 11, 'go_home': 11, 'indoor_backup': 11, 'indoor_visit': 11, 'meal': 11, 'short_walk': 11, 'sunset_finish': 11}

## Recommended first modeling task
### Task 1: `next_scene` multiclass classification
Use these columns as features:
- duration_type
- weather_type
- rain_prob
- dust_level
- hour
- trip_goal
- current_place_type
- companion_type
- adult_count
- child_count
- transport
- activity_level
- avg_stay_minutes
- indoor_ratio
- event_active
- event_schedule_known
- tags (multi-hot after splitting `|`)
- hunger
- fatigue
- need_indoor
- keep_mood
- move_tolerance
- kids_tolerance
- photo_motivation

Exclude:
- scenario_id
- next_scene (target)
- meal_style_primary / secondary
- confidence_grade
- course_depth (exclude if you want a cleaner pure next-scene model; include only if treated as known policy signal)

Suggested models:
- LightGBM
- XGBoost
- RandomForest
- CatBoost (works well with categoricals)

Recommended metrics:
- Macro F1
- Per-class recall
- Confusion matrix

## Secondary modeling task
### Task 2: `course_depth` classification
Classes:
- 2
- 3
- 4

Use the same feature set as above, excluding next_scene and meal_style labels.

## Caution about meal-style modeling
`meal_style_primary` is currently only populated for `next_scene = meal` cases, so it has only 70 labeled rows.

Current class distribution:
{'family_relaxed_meal': 36, 'warm_comfort_meal': 14, 'hearty_refuel_meal': 12, 'photo_brunch_meal': 4, 'light_quick_meal': 3, 'quiet_rest_meal': 1}

This is strongly imbalanced, so `meal_style_primary` is **not yet a robust standalone training target** unless you add more scenarios for the rare classes:
- quiet_rest_meal
- light_quick_meal
- photo_brunch_meal

For now, use it for:
- rule validation
- exploratory modeling only
- later expansion

## Suggested preprocessing
### Categorical columns
One-hot encode or use CatBoost-native categoricals:
- duration_type
- weather_type
- dust_level
- trip_goal
- current_place_type
- companion_type
- transport
- activity_level

### Binary columns
Keep as 0/1:
- event_active
- event_schedule_known

### Numeric columns
Use as-is:
- rain_prob
- hour
- adult_count
- child_count
- avg_stay_minutes
- indoor_ratio
- hunger
- fatigue
- need_indoor
- keep_mood
- move_tolerance
- kids_tolerance
- photo_motivation

### Tags column
Split `tags` on `|`, then multi-hot encode.
Examples:
- family_friendly
- festival_event
- healing
- indoor_comfort
- interactive
- kids_friendly
- photo_friendly
- quiet
- scenic

## Recommended experimental order
1. `next_scene` multiclass classification
2. `course_depth` classification
3. expand dataset, then revisit `meal_style_primary`
4. later: candidate ranking / suitability scoring

## Important positioning
This dataset is **not real user-behavior log data**.
It is a **synthetic scenario-based weak-supervision dataset** built from explicit labeling rules and scenario design.
Use it for:
- policy learning / policy calibration
- next-scene modeling
- initial recommendation logic validation

Do not claim:
- direct real-user preference learning
- market-scale behavioral generalization