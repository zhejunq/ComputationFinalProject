# /!usr/bin/env python3

# import
import geopandas as gpd
import osmnx as ox
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import LineString, Point
import speed_cal

# get osm map
place_name = "Municipio de Tijuana, Baja California, Mexico"
place_name2 = "Salingyi, Sagaing, Myanmar"
# DK placename? see https://nominatim.openstreetmap.org/
graph = ox.graph_from_place(place_name, network_type="drive")
graph2 = ox.graph_from_place(place_name2)
# If you want to extract all the information from a small area, try graph = ox.graph_from_place(place_name, network_type="drive")


# project graph network (for more accurate calculation)
graph_proj = ox.project_graph(graph)
graph_proj2 = ox.project_graph(graph2)


# get areas gdf
area = ox.geocode_to_gdf(place_name)
area_proj = ox.project_gdf(area)

# retreve buildings:
# tags = {'building': True}
tags = {"amenity": "police"}
police_station = ox.geometries_from_place(place_name, tags=tags)
# not buildings_from_place
police_station_proj = ox.project_gdf(police_station)

# convert nx.graph to gdf
nodes, edges = ox.graph_to_gdfs(graph_proj)
edges["highway"] = edges["highway"].astype(str)
edges["highway"].unique()
trunkway = edges.loc[edges["highway"] == "trunk", :]

# visualize the OSM:
fig, ax = plt.subplots()
area_proj.plot(ax=ax, facecolor="black")
# edges.plot(ax=ax, linewidth=1, edgecolor='#8C8F8F')
trunkway.plot(ax=ax, linewidth=1, edgecolor="#8C8F8F")
police_station_proj.plot(ax=ax, facecolor="khaki", alpha=0.7)
plt.show()

# extended_stats has been removed

# Compute betweenness centrality and closeness centrality
nodes2, edges2 = ox.graph_to_gdfs(graph_proj2)

betweenness_centrality = nx.betweenness_centrality(graph_proj2, weight="length")
closeness_centrality = nx.closeness_centrality(graph_proj2, distance="length")

# concate betweenness to nodes
nodes2["betweenness"] = nodes2.index.map(betweenness_centrality)
# Normalize betweenness centrality values to a 0-1 scale for better coloring
nodes2["betweenness_normalized"] = nodes2["betweenness"] / max(nodes2["betweenness"])

# Plot the graph with nodes colored based on betweenness centrality
fig, ax2 = plt.subplots(figsize=(10, 10))
ax2.set_aspect("equal")
edges2.plot(ax=ax2, edgecolor="gray", linewidth=0.5)
nodes2.plot(ax=ax2, column="betweenness_normalized", cmap="plasma", legend=True)
ax2.set_title("Nodes colored by betweenness centrality")
ax2.set_xlabel("Longitude")
ax2.set_ylabel("Latitude")
plt.show()

# speed calculation
edges["maxspeed"] = pd.to_numeric(edges["maxspeed"], errors="coerce")
edges["maxspeed"].value_counts(dropna=False)
edges = edges.loc[
    ~edges["highway"].isin(["cycleway", "footway", "pedestrian", "trail", "crossing"])
].copy()

mask = edges["maxspeed"].isnull()
edges_without_maxspeed = edges.loc[mask].copy()
edges_with_maxspeed = edges.loc[~mask].copy()
edges_without_maxspeed["maxspeed"] = edges_without_maxspeed["highway"].apply(
    speed_cal.road_class_to_kmph
)
edges = pd.concat([edges_with_maxspeed, edges_without_maxspeed], ignore_index=True)

# Convert the value into regular integer Series (the plotting requires having Series instead of IntegerArray)
edges["maxspeed"] = edges["maxspeed"].astype(int)

# plot edges based on maxspeed
fig, ax3 = plt.subplots(figsize=(10, 10))
ax3.set_aspect("equal")
ax3.set_title("Tijuana driving roads weighted by Maxspeed")
edges.plot(ax=ax3, column="maxspeed", legend=True)
ax3.set_xlabel("Longitude")
ax3.set_ylabel("Latitude")
plt.show()

# calculate traveling time
edges["travel_time_minutes"] = (edges["length"] / (edges["maxspeed"] / 3.6)) / 60
edges.loc[0:10, ["maxspeed", "highway", "travel_time_minutes"]]
# plot map with traveling times
fig, ax4 = plt.subplots(figsize=(10, 10))
ax4.set_aspect("equal")
ax4.set_title("Tijuana driving roads weighted by travelling time")
edges.plot(ax=ax4, column="travel_time_minutes", legend=True)
ax4.set_xlabel("Longitude")
ax4.set_ylabel("Latitude")
plt.show()


# Calculate shortest route from central to the territory

centroid = (
    edges.unary_union.convex_hull.centroid
)  # calculate the centroid of the street network as the origin location
nodes["y"] = nodes["y"].astype(
    float
)  # convert y coordinotes to floating point numbersi

maxy = nodes[
    "y"
].max()  # find the Northern-most y-coordinate and extract the row from the DF
target_loc = nodes.loc[nodes["y"] == maxy, :]

target_point = target_loc.geometry.values[0]  # extract the geometry


st_node_id, dist_to_st = ox.distance.nearest_nodes(
    graph_proj, centroid.x, centroid.y, return_dist=True
)
ed_node_id, dist_to_ed = ox.distance.nearest_nodes(
    graph_proj, target_point.x, target_point.y, return_dist=True
)
print("Starting node-id:", st_node_id, "and distance:", dist_to_st, "meters.")
print("Ending node-id:", ed_node_id, "and distance:", dist_to_ed, "meters.")

rt1 = nx.shortest_path(
    graph_proj, source=st_node_id, target=ed_node_id, weight="length"
)
rt2 = nx.shortest_path(
    graph_proj, source=st_node_id, target=ed_node_id, weight="travel_time_minutes"
)

# plot the two routes
fig, ax5 = ox.plot_graph(graph_proj, figsize=(10, 10), close=False, show=False)
ox.plot_graph_route(graph_proj, rt1, ax=ax5, close=False, show=False, route_color="red")
ox.plot_graph_route(
    graph_proj, rt2, ax=ax5, close=False, show=False, route_color="orange"
)
ax5.set_aspect("equal")
ax5.set_title("Shortest road from city centre to territory, Tijuana")

plt.show()
# OSM data is in WGS84 so typically we need to use lat/lon coordinates when searching for the closest node

# Destination
dest_address = "Delfin del Pacifico, Municipio de Tijuana"
dest_y, dest_x = ox.geocode(dest_address)  # notice the coordinate order (y, x)!
dest = Point(dest_x, dest_y)
dest = ox.projection.project_geometry(dest)

# Origin
orig_address = "Delegacion Playas, Municipio de Tijuana"
orig_y, orig_x = ox.geocode(orig_address)
orig = Point(orig_x, orig_y)
orig = ox.projection.project_geometry(orig)

print("Origin coords:", orig_x, orig_y)
print("Destination coords:", dest_x, dest_y)

# 1. Find the closest nodes for origin and destination
orig_node_id, dist_to_orig = ox.distance.nearest_nodes(
    graph_proj, orig[0].x, orig[0].y, return_dist=True
)
dest_node_id, dist_to_dest = ox.distance.nearest_nodes(
    graph_proj, dest[0].x, dest[0].y, return_dist=True
)

print("Origin node-id:", orig_node_id, "and distance:", dist_to_orig, "meters.")
print("Destination node-id:", dest_node_id, "and distance:", dist_to_dest, "meters.")

metric_path = nx.dijkstra_path(
    graph_proj, source=orig_node_id, target=dest_node_id, weight="length"
)  # get the route
time_path = nx.dijkstra_path(
    graph_proj, source=orig_node_id, target=dest_node_id, weight="travel_time_minutes"
)

# Get also the actual travel times (summarize)
travel_length = nx.dijkstra_path_length(
    graph_proj, source=orig_node_id, target=dest_node_id, weight="length"
)
travel_time = nx.dijkstra_path_length(
    graph_proj, source=orig_node_id, target=dest_node_id, weight="travel_time_minutes"
)

# Shortest path map
fig, ax6 = ox.plot_graph(graph_proj, figsize=(10, 10), close=False, show=False)
ox.plot_graph_route(
    graph_proj, metric_path, ax=ax6, close=False, show=False, route_color="red"
)
ox.plot_graph_route(
    graph_proj, time_path, ax=ax6, close=False, show=False, route_color="orange"
)
ax6.set_title(
    "Shortest path distance {t: .1f} meters, travel time {p: .1f} minutes.".format(
        t=travel_length, p=travel_time
    )
)
plt.show()

time_path_nodes = nodes.loc[time_path]
time_path_line = LineString(list(time_path_nodes.geometry.values))
