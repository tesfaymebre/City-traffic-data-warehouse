with source as (
    select * from {{ source('raw', 'vehicle_tracks') }}
),

cleaned as (
    select
        track_id,
        trim(vehicle_type) as vehicle_type,
        traveled_distance,
        avg_speed,
        source_file,
        capture_date,
        area_code,
        time_window_start,
        time_window_end,
        {{ format_time_window('time_window_start', 'time_window_end') }} as capture_time_window,
        loaded_at
    from source
    where track_id is not null
)

select * from cleaned
