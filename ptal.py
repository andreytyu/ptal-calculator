import geopandas as gpd
import pandas as pd 
import ptal_tools
import os
from tqdm import tqdm


gtfs_path = os.getenv('data_path')
osrm_url = os.getenv('osrm_url')

stops = pd.read_csv(gtfs_path+'stops.txt')
stop_times = pd.read_csv(gtfs_path+'stop_times.txt')
routes = pd.read_csv(gtfs_path+'routes.txt')
trips = pd.read_csv(gtfs_path+'trips.txt')

grid = ptal_tools.create_fishnet(stops.stop_lon.min(), stops.stop_lon.max(), stops.stop_lat.min(),  stops.stop_lat.max(), 0.1)
grid['centroid'] = grid['geometry'].centroid

frequency_df = ptal_tools.frequency_on_stops(trips, routes, stop_times)
frequency_df = frequency_df[frequency_df.route_type.isin(range(4))].reset_index(drop=True)

ais = []
ids = []
for x in tqdm(range(len(grid))):
    test_point = grid['centroid'][x]
    stops_to_consider = ptal_tools.close_stops(test_point, stops)
    
    durations = []
    for y in range(len(stops_to_consider)):
        durations.append(ptal_tools.osrm_route_duration(test_point.x,
                                                        test_point.y,
                                                        stops_to_consider['stop_lon'][y],
                                                        stops_to_consider['stop_lat'][y],
                                                        osrm_url))
    stops_to_consider['duration'] = durations
    stops_to_consider = pd.merge(stops_to_consider, frequency_df, on='stop_id')
    stops_to_consider = stops_to_consider.sort_values(by=[
    'stop_name', 'route_id', 'duration'
    ]).drop_duplicates(subset=['stop_name', 'route_id'], keep='first').reset_index(drop=True)
    
    edfs = []
    for z in range(len(stops_to_consider)):
        swt = 0.5 * (60 / stops_to_consider['frequency'][z])
        if stops_to_consider['route_type'][z] in [0,1,2]:
            awt = swt + 0.7
        else:
            awt = swt + 2
        tat = awt + stops_to_consider['duration'][z]
        edf = 0.5 * (60 / tat)
        edfs.append(edf)
        #print(edf)
    stops_to_consider['edf'] = edfs
    
    types = stops_to_consider['route_type'].unique()
    ai = []
    for v in range(len(types)):
        tempo = stops_to_consider[stops_to_consider['route_type'] == types[v]].sort_values(by='edf', ascending=False).reset_index(drop=True)
        if types[v] in [0,1,2]:
            tempo = tempo[tempo['duration'] < 12.1].reset_index(drop=True)
        else:
            tempo = tempo[tempo['duration'] < 8.1].reset_index(drop=True)
        if len(tempo) > 1:
            ai.append(tempo['edf'][0] + 0.5 * tempo[1:]['edf'].sum())
        if len(tempo) == 1:
            ai.append(tempo['edf'][0])
        else:
            ai.append(0)
    ais.append(sum(ai))
    ids.append(grid['cell_id'][x])