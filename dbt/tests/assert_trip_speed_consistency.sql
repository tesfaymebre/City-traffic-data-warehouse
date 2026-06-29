/*
  Singular test: flag trips where trip-level avg_speed diverges sharply
  from the mean of instantaneous point speeds (possible extraction anomaly).
  Returns failing rows; test passes when zero rows returned.
*/
select
    track_id,
    source_file,
    avg_speed,
    mean_point_speed,
    abs(avg_speed - mean_point_speed) as speed_gap_mps
from {{ ref('mart_vehicle_trip_summary') }}
where abs(avg_speed - mean_point_speed) > 5
