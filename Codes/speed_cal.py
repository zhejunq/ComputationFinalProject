#!/usr/bin/env python3


def road_class_to_kmph(road_class):
    if road_class == "motorway":
        return 110
    elif road_class == "motorway_link":
        return 100
    elif road_class in ["primary", "primary_link"]:
        return 90
    elif road_class in ["trunk", "trunk_link", "secondary", "secondary_link"]:
        return 80
    elif road_class in ["residential", "steps", "path", "living_street"]:
        return 10
    else:
        return 60
