# Chungnam Synthetic Scenario Dataset (490 rows)

This file is a **scenario-based weak supervision dataset**, not real user behavior logs.

## Purpose
Designed for early-stage training / validation of:
- next_scene classification
- meal_style classification
- course_depth branching
- recommendation-policy tuning

## Balancing strategy
- Total rows: 490
- next_scene classes: perfectly balanced at 70 each
- duration / weather / companion / goal distributions are reasonably diverse, but not perfectly equalized

## Current distribution
- duration_counts: {"half_day": 179, "full_day": 178, "2h": 133}
- weather_counts: {"cloudy": 175, "sunny": 160, "rainy": 155}
- goal_counts: {"indoor": 118, "healing": 113, "family": 103, "experience": 91, "photo": 65}
- place_counts: {"cafe_area": 105, "history": 82, "photo_spot": 79, "indoor_culture": 78, "festival": 73, "nature": 73}
- companion_counts: {"family_medium": 86, "couple": 84, "friends": 83, "family_large": 82, "solo": 81, "family_small": 74}
- next_scene_counts: {"meal": 70, "sunset_finish": 70, "short_walk": 70, "go_home": 70, "indoor_visit": 70, "indoor_backup": 70, "cafe_rest": 70}

## Important caution
Use this as:
- policy-learning support
- weak supervision data
- synthetic scenario benchmark

Do not describe it as:
- real-world behavioral log data
- true revealed preference data

## Key columns
- scenario_id
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
- tags
- hunger
- fatigue
- need_indoor
- keep_mood
- move_tolerance
- kids_tolerance
- photo_motivation
- course_depth
- next_scene
- meal_style_primary
- meal_style_secondary
- confidence_grade
