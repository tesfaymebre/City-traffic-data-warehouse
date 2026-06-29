-- KPI: total GPS trajectory samples
select count(*) as total_gps_points
from marts.fct_trajectory_points
