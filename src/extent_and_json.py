#!/bin/python

from pathlib import Path
from shapely import Polygon, to_wkt

import argparse
import geopandas as gpd
import json
import numpy as np
import pdal
import sys


def parse_arguments():
    '''parses the arguments, returns args'''
    # init parser
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--in_laz',
        type=str,
        required=True,
        help='Path to input las/z file'
    )

    parser.add_argument(
        '--out_dir',
        type=str,
        required=True,
        help='Path to directory where results will be written'
    )

    parser.add_argument(
        '--buildings',
        type=str,
        required=True,
        help='Vector file of building footprints.'
    )

    parser.add_argument(
        '--tmp_dir',
        type=str,
        required=True,
        help='directory for tmp files.'
    )

    parser.add_argument(
        '--out_srs',
        type=int,
        required=True,
        help='Integer portion of EPSG code of desired output.'
    )

    args = parser.parse_args()
    args.buildings = Path(args.buildings).resolve()
    args.in_laz = Path(args.in_laz).resolve()
    args.out_dir = Path(args.out_dir).resolve()
    args.tmp_dir = Path(args.tmp_dir).resolve()

    return args


def get_extent(laz):
    pipe = pdal.Reader.las(filename=laz).pipeline()
    p = pipe.execute()
    
    arr = pipe.arrays[0]
    minx = np.min(arr[0]['X'])
    maxx = np.max(arr[0]['X'])
    miny = np.min(arr[0]['Y'])
    maxy = np.max(arr[0]['Y'])

    return Polygon((
        (minx, miny),
        (minx, maxy),
        (maxx, maxy),
        (maxx, miny),
        (minx, miny)
    )) 


def write_pipeline(extent, layer, out_laz, pipe_path):

    pipeline = [
        {
            'tag': 'read',
            'type': 'readers.las',
            'filename':str(ARGS.in_laz)
        },
        {
            'tag': 'ovrly',
            'column': 'class',
            'datasource': str(extent),
            'dimension': 'Classification',
            'type': 'filters.overlay'
        },
        {
            'tag': 'exp',
            'expression': 'Classification != 6',
            'type': 'filters.expression'
        },
        {
            'tag': 'wrt',
            'type': 'writers.las',
            'filename': str(out_laz)
        }
    ]

    with open(str(pipe_path), 'w') as f:
        json.dump(pipeline, f, indent=4)



ARGS = parse_arguments()

# make tmp_dir
ARGS.tmp_dir.mkdir(exist_ok=True)

# read buildings
buildings = gpd.read_file(ARGS.buildings)

# set crs for buildings
buildings = buildings.to_crs(epsg=ARGS.out_srs)

# make a class column filled with 6
buildings['class'] = 6

# get extent
extent = get_extent(ARGS.in_laz)

##### DEBUG
gpd.GeoDataFrame(geometry=[extent]).set_crs(ARGS.out_srs).to_file('WTF.geojson')
print(buildings.geometry.within(gpd.GeoDataFrame(geometry=[extent]).set_crs(ARGS.out_srs)).any())


# save extent as gpkg
extent_path = ARGS.tmp_dir / f'{ARGS.in_laz.stem}.gpkg'
layer = 'data'
_ = gpd.clip(buildings, extent).set_crs(epsg=ARGS.out_srs).to_file(
    extent_path,
    layer=layer,
    driver='GPKG')

# path names for files
out_laz = ARGS.out_dir / f'{ARGS.in_laz.stem}_noBuildings.laz'
pipe_path = ARGS.tmp_dir / f'{ARGS.in_laz.stem}.json'

write_pipeline(extent_path, layer, out_laz, pipe_path)