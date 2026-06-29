-- Table: full traffic summary by area, date, window, and vehicle type
select
    area_code,
    capture_date,
    capture_time_window,
    vehicle_type,
    vehicle_count,
    avg_speed_mps,
    avg_distance_meters,
    avg_trip_duration_seconds,
    peak_speed_mps
from marts.mart_traffic_by_vehicle_type
order by capture_date, capture_time_window, vehicle_type
