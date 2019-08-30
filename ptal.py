import geopandas as gpd
import pandas as pd 
import ptal_tools
import os
from tqdm import tqdm

variable_test = os.getenv('ANDREY')
gtfs_path = os.getenv('data_path')

print(os.getcwd())

stops = pd.read_csv(gtfs_path+'stops.txt')
stop_times = pd.read_csv(gtfs_path+'stop_times.txt')
routes = pd.read_csv(gtfs_path+'routes.txt')
trips = pd.read_csv(gtfs_path+'trips.txt')

grid = ptal_tools.create_fishnet(stops.stop_lon.min(), stops.stop_lon.max(), stops.stop_lat.min(),  stops.stop_lat.max(), 0.1)
grid['centroid'] = grid['geometry'].centroid

df = ptal_tools.frequency_on_stops(trips, routes, stop_times)

ais = []
ids = []
for x in tqdm(range(len(grid))):
    test_point = grid['centroid'][x]
    o = ptal_tools.close_stops(test_point, stops)
    
    durations = []
    for y in range(len(o)):
        durations.append(ptal_tools.osrm_route_duration(test_point.x, test_point.y, o['stop_lon'][y], o['stop_lat'][y]))
    o['duration'] = durations
    
    o = pd.merge(o, df, on='stop_id')
    
    o[(o['route_type'] == 0)|
      (o['route_type'] == 1)|
      (o['route_type'] == 2)|
      (o['route_type'] == 3)
     ]
    
    o = o.sort_values(by=[
    'stop_name', 'route_id', 'duration'
    ]).drop_duplicates(subset=['stop_name', 'route_id'], keep='first').reset_index(drop=True)
    
    edfs = []
    for z in range(len(o)):
        swt = 0.5 * (60 / o['frequency'][z])
        if o['route_type'][z] in [0,1,2]:
            awt = swt + 0.7
        else:
            awt = swt + 2
        tat = awt + o['duration'][z]
        edf = 0.5 * (60 / tat)
        edfs.append(edf)
        #print(edf)
    o['edf'] = edfs
    
    types = o['route_type'].unique()
    
    ai = []
    for v in range(len(types)):
        
        tempo = o[o['route_type'] == types[v]].sort_values(by='edf', ascending=False).reset_index(drop=True)
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