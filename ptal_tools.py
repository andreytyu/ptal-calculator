import geopandas as gpd
from math import ceil
from shapely.geometry import Polygon
import pandas as pd
import requests
from geopy.distance import geodesic
from scipy.spatial.distance import cdist

osrm_error_msg = '''⚠️ OSRM url not specified ⚠️'''

def create_fishnet(minlon, maxlon, minlat,  maxlat, cellsize):
    rows = ceil((maxlat - minlat) / cellsize)
    cols = ceil((maxlon - minlon) / cellsize)

    x_left_origin = minlon
    x_right_origin = minlon + cellsize
    y_top_origin = maxlat
    y_bottom_origin = maxlat - cellsize

    geoms = []
    for col in range(cols):
        y_top = y_top_origin
        y_bottom = y_bottom_origin
        for row in range(rows):
            geoms.append(
                Polygon([
                    (x_left_origin, y_top),
                    (x_right_origin, y_top),
                    (x_right_origin, y_bottom),
                    (x_left_origin, y_bottom)
                    ]))
            y_top = y_top - cellsize
            y_bottom = y_bottom - cellsize
        x_left_origin = x_left_origin + cellsize
        x_right_origin = x_right_origin + cellsize
    
    fishnet = gpd.GeoDataFrame(geometry=geoms)
    fishnet['cell_id'] = range(len(fishnet))
    return fishnet

def frequency_on_stops(trips, routes, stop_times):
    stop_times['arrival_time'] = stop_times['arrival_time'].apply(lambda x: datetime.strptime(x, '%H:%M:%S').time())
    stop_times = stop_times[( stop_times['arrival_time'] >= datetime.strptime('08:15:00', '%H:%M:%S').time()) & (stop_times['arrival_time'] <= datetime.strptime('09:15:00', '%H:%M:%S').time())].reset_index(drop=True)
    trips_w_types = pd.merge(trips, routes, on='route_id')[['trip_id', 'route_id', 'route_type']]
    df = pd.merge(stop_times, trips_w_types, on='trip_id')[['trip_id','arrival_time','stop_id', 'route_id', 'route_type']]
    df = df.groupby(by=['stop_id','route_id'], as_index=False).count()[['stop_id','route_id','trip_id']]
    df.columns = ['stop_id', 'route_id', 'frequency']
    df = pd.merge(df, routes, on='route_id')[['stop_id', 'route_id', 'route_type', 'frequency']]
    return df
            
def osrm_route_duration(x1,y1,x2,y2, osrm_url):
    if not osrm_url:
        raise ValueError(osrm_error_msg)
    req = osrm_url+'%f,%f;%f,%f'%(x1, y1, x2, y2)
    r = requests.get(req)
    duration = r.json()['routes'][0]['duration'] / 60                    
    return(duration)

def near_stops(point, stops_df):
    lens = []
    for x in range(len(stops_df)):
        lens.append(round(geodesic((point.x, point.y), (stops_df['stop_lon'][x], stops_df['stop_lat'][x])).meters, 3))
    stops_df['lens'] = lens
    stops_df = stops_df[stops_df['lens'] < 1500]
    return stops_df

def close_stops(point, stops):
    stops_df = stops[(cdist([[point.x, point.y]], stops[['stop_lon', 'stop_lat']])<0.02)[0]].reset_index(drop=True)
    return stops_df
