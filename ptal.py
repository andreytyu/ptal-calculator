import geopandas as gpd
import pandas as pd 
import ptal_tools as t
import os
from tqdm import tqdm
from shapely.geometry import Point

gtfs_path = os.getenv('data_path')
osrm_url = os.getenv('osrm_url')

stops = pd.read_csv(gtfs_path+'stops.txt')
stop_times = pd.read_csv(gtfs_path+'stop_times.txt')
routes = pd.read_csv(gtfs_path+'routes.txt')
trips = pd.read_csv(gtfs_path+'trips.txt')

transformed = gpd.GeoDataFrame(geometry=[Point(stops.stop_lon.min(),stops.stop_lat.min()),
Point(stops.stop_lon.max(),stops.stop_lat.max())])
transformed.crs = {'init' :'epsg:4326'}
with open('transformed.geojson', 'w') as f:
    f.write(transformed.to_json())


print(transformed)
transformed = transformed.to_crs(epsg=3857)

with open('transformed_58.geojson', 'w') as f:
    f.write(transformed.to_json())

print(transformed)
grid = t.create_fishnet(transformed.geometry[0].x, transformed.geometry[1].x, transformed.geometry[0].y,  transformed.geometry[1].y, 1000)
print(transformed.geometry[0].x, transformed.geometry[1].x, transformed.geometry[0].y,  transformed.geometry[1].y)
grid.crs = {'init' :'epsg:3857'}
grid = grid.to_crs(epsg=4326)
grid['centroid'] = grid['geometry'].centroid

stop_times['arrival_time'] = stop_times['arrival_time'].apply(lambda x: t.fix_time_after_midnight(x))

frequency_df = t.frequency_on_stops(trips, routes, stop_times)
frequency_df = frequency_df[frequency_df.route_type.isin(range(4))].reset_index(drop=True)
awts = []
for x in range(len(frequency_df)):
    swt = 0.5 * (60 / frequency_df['frequency'][x])
    if frequency_df['route_type'][x] in range(3):
        awts.append(swt + 0.7)
    else:
        awts.append(swt + 2)
frequency_df['awt'] = awts


ais = []
for x in tqdm(range(len(grid))):
    test_point = grid['centroid'][x]
    stops_to_consider = t.close_stops(test_point, stops)
    
    durations = []
    for y in range(len(stops_to_consider)):
        durations.append(t.osrm_route_duration(test_point.x,
                                                test_point.y,
                                                stops_to_consider['stop_lon'][y],
                                                stops_to_consider['stop_lat'][y],
                                                osrm_url))
    stops_to_consider['duration'] = durations
    stops_to_consider = pd.merge(stops_to_consider, frequency_df, on='stop_id')
    stops_to_consider = stops_to_consider.sort_values(by=[
    'stop_name', 'route_id', 'duration'
    ]).drop_duplicates(subset=['stop_name', 'route_id'], keep='first').reset_index(drop=True)
    stops_to_consider['edf'] = 0.5 * (60 / (stops_to_consider['awt'] + stops_to_consider['duration']))
    
    types = stops_to_consider['route_type'].unique()
    ai = []
    for stop_type in types:
        tempo = stops_to_consider[stops_to_consider['route_type'] == stop_type].sort_values(by='edf', ascending=False).reset_index(drop=True)
        if stop_type in range(3):
            tempo = tempo[tempo['duration'] <= 12].reset_index(drop=True)
        else: # stop_type == 3
            tempo = tempo[tempo['duration'] <= 8].reset_index(drop=True)

        if len(tempo) > 1:
            ai.append(tempo['edf'][0] + 0.5 * tempo[1:]['edf'].sum())
        elif len(tempo) == 1:
            ai.append(tempo['edf'][0])
        else:
            ai.append(0)
    ais.append(sum(ai))

grid['ai'] = ais
grid.drop('centroid', inplace=True, axis=1)
with open('grid.geojson', 'w') as f:
    f.write(grid.to_json())