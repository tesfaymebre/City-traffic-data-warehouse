with source as (
    select * from {{ source('raw', 'trajectory_points') }}
),

cleaned as (
    select
        track_id,
        source_file,
        point_index,
        latitude,
        longitude,
        speed,
        lon_acceleration,
        lat_acceleration,
        recorded_at
    from source
    where
        latitude between 37.0 and 38.5
        and longitude between 23.0 and 24.5
        and speed >= 0
)

select * from cleaned
