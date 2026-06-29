with trip_summary as (
    select * from {{ ref('mart_vehicle_trip_summary') }}
)

select
    area_code,
    capture_date,
    capture_time_window,
    vehicle_type,
    count(*) as vehicle_count,
    round(avg(avg_speed)::numeric, 2) as avg_speed_mps,
    round(avg(traveled_distance)::numeric, 2) as avg_distance_meters,
    round(avg(trip_duration_seconds)::numeric, 2) as avg_trip_duration_seconds,
    round(max(max_speed)::numeric, 2) as peak_speed_mps
from trip_summary
group by 1, 2, 3, 4
