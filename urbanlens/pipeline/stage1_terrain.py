"""
stage1_terrain.py – Builds the 256x256 terrain mesh in Blender from dem_256.npy.
"""

import os
import json
import numpy as np
import bpy
import mathutils

meta_path = os.path.abspath("data/processed/dem_256_meta.json")
npy_path = os.path.abspath("data/processed/dem_256.npy")

with open(meta_path, "r") as f:
    meta = json.load(f)

dem_256 = np.load(npy_path)
width_m = meta["width_m"]    # 9800.0 m
height_m = meta["height_m"]  # 9200.0 m
min_elev = meta["min_elev"]  # 736.0 m
max_elev = meta["max_elev"]  # 940.0 m

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

N = 256
xs = np.linspace(-width_m / 2.0, width_m / 2.0, N)
ys = np.linspace(height_m / 2.0, -height_m / 2.0, N)

verts = []
for r in range(N):
    y = float(ys[r])
    for c in range(N):
        x = float(xs[c])
        z = float(dem_256[r, c])
        verts.append((x, y, z))

faces = []
for r in range(N - 1):
    for c in range(N - 1):
        v0 = r * N + c
        v1 = r * N + (c + 1)
        v2 = (r + 1) * N + (c + 1)
        v3 = (r + 1) * N + c
        faces.append((v0, v1, v2, v3))

mesh = bpy.data.meshes.new("TerrainMesh")
mesh.from_pydata(verts, [], faces)
mesh.update()

# Add UV Map (0 to 1)
uv_layer = mesh.uv_layers.new(name="UVMap")
for poly in mesh.polygons:
    for loop_idx in poly.loop_indices:
        vert_idx = mesh.loops[loop_idx].vertex_index
        r = vert_idx // N
        c = vert_idx % N
        u = c / (N - 1)
        v = 1.0 - (r / (N - 1))
        uv_layer.data[loop_idx].uv = (u, v)

obj = bpy.data.objects.new("Terrain", mesh)
bpy.context.collection.objects.link(obj)

# Expose vertical exaggeration as a labeled property
obj["vertical_exaggeration"] = 1.0
obj.id_properties_ui("vertical_exaggeration").update(
    description="Vertical exaggeration multiplier (1.0 = 1x real metres)",
    default=1.0,
    min=0.1,
    max=10.0,
    soft_min=0.5,
    soft_max=5.0
)

obj["min_elevation_m"] = min_elev
obj["max_elevation_m"] = max_elev
obj["width_m"] = width_m
obj["height_m"] = height_m

# Driver for vertical exaggeration: scale Z
fcurve = obj.driver_add("scale", 2)
driver = fcurve.driver
driver.type = 'AVERAGE'
var = driver.variables.new()
var.name = "exag"
var.type = 'SINGLE_PROP'
target = var.targets[0]
target.id_type = 'OBJECT'
target.id = obj
target.data_path = '["vertical_exaggeration"]'

# Save blend file
out_blend = os.path.abspath("urbanlens.blend")
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("Saved urbanlens.blend successfully!")

total_verts = len(mesh.vertices)
bbox = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
min_x = min(v.x for v in bbox)
max_x = max(v.x for v in bbox)
min_y = min(v.y for v in bbox)
max_y = max(v.y for v in bbox)
min_z = min(v.z for v in bbox)
max_z = max(v.z for v in bbox)

print(f"VERTS_COUNT: {total_verts}")
print(f"BBOX_METRES: X=[{min_x:.2f}, {max_x:.2f}] (width: {max_x - min_x:.2f} m), Y=[{min_y:.2f}, {max_y:.2f}] (height: {max_y - min_y:.2f} m), Z=[{min_z:.2f}, {max_z:.2f}]")
print(f"VERTICAL_RANGE_METRES: {max_z - min_z:.2f} m (Min: {min_z:.2f} m, Max: {max_z:.2f} m)")
