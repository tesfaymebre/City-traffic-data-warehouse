-- Bar chart: peak recorded speed by vehicle type (m/s)
select
    vehicle_type,
    max(peak_speed_mps) as peak_speed_mps
from marts.mart_traffic_by_vehicle_type
group by vehicle_type
order by peak_speed_mps desc
