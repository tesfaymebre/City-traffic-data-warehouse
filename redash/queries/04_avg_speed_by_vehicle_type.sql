-- Bar chart: average speed by vehicle type (m/s)
select
    vehicle_type,
    round(avg(avg_speed_mps)::numeric, 2) as avg_speed_mps
from marts.mart_traffic_by_vehicle_type
group by vehicle_type
order by avg_speed_mps desc
