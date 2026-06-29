with tracks as (
    select * from {{ ref('stg_vehicle_tracks') }}
),

points as (
    select * from {{ ref('stg_trajectory_points') }}
),

point_stats as (
    select
        track_id,
        source_file,
        count(*) as point_count,
        max(speed) as max_speed,
        avg(speed) as mean_point_speed,
        max(recorded_at) as trip_duration_seconds
    from points
    group by 1, 2
)

select
    tracks.track_id,
    tracks.source_file,
    tracks.vehicle_type,
    tracks.area_code,
    tracks.capture_date,
    tracks.capture_time_window,
    tracks.traveled_distance,
    tracks.avg_speed,
    point_stats.point_count,
    point_stats.max_speed,
    point_stats.mean_point_speed,
    point_stats.trip_duration_seconds
from tracks
inner join point_stats
    on tracks.track_id = point_stats.track_id
    and tracks.source_file = point_stats.source_file
