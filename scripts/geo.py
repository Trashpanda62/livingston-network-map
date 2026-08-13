"""Shared local projection for the Livingston city map.

One frame everywhere: scene units east/south of the courthouse square,
1 unit = 12 m, +x east, +z south (north = -z on the three.js ground).
"""
import math

LAT0, LON0 = 36.3839, -85.3227  # courthouse square
M_PER_UNIT = 12.0


def to_local(lat, lon):
    x = (lon - LON0) * math.cos(math.radians(LAT0)) * 111320.0 / M_PER_UNIT
    z = -(lat - LAT0) * 110540.0 / M_PER_UNIT
    return [round(x, 2), round(z, 2)]
