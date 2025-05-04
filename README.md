# lidar_toolz

Some Tools for simple lidar tasks.

 ----
## src/clip_buildings.sh 
Usage:
```
bash clip_buildings.sh \
    -i path/to/laz/files \
    -o path/to/output \
    -c path/to/buildings.geojson \
    -s 26910
```

```
Removes points lying within polygons (e.g. building footprints)
from point clouds.
        
     options:
        -h - Display help
        
     arguments:
        -i [input_dir] - Path to input directory
        -o [output_dir] - Path to directory where clipped point
         clouds will be written.
        -c [clip_polygons] - OGR readable polygon layer.  Points
        lying within polygons will be removed.
        -s [srs] - srs as numerical portion of EPSG code,
        e.g. 26910 (for EPSG:26910)

```

### src/extent_and_json.py
Creates temporary files used by  `src/clip_buildings.sh`. 