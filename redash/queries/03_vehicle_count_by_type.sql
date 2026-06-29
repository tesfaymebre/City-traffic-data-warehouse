-- Bar chart: vehicle mix by type
select
    vehicle_type,
    sum(vehicle_count) as vehicle_count
from marts.mart_traffic_by_vehicle_type
group by vehicle_type
order by vehicle_count desc
