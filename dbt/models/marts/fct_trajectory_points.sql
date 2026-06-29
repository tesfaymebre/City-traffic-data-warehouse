with tracks as (
    select * from {{ ref('stg_vehicle_tracks') }}
),

points as (
    select * from {{ ref('stg_trajectory_points') }}
)

select
    points.track_id,
    points.source_file,
    points.point_index,
    points.latitude,
    points.longitude,
    points.speed,
    points.lon_acceleration,
    points.lat_acceleration,
    points.recorded_at,
    tracks.vehicle_type,
    tracks.traveled_distance,
    tracks.avg_speed as track_avg_speed,
    tracks.capture_date,
    tracks.area_code,
    tracks.capture_time_window
from points
inner join tracks
    on points.track_id = tracks.track_id
    and points.source_file = tracks.source_file
