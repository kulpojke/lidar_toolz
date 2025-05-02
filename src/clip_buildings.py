#!/bin/python
# usage:
# python src/clip_buildings.py --aoi=vectors/Eaton_Perimeter_20250121.geojson --buildings=vectors/eaton_buildings.geojson --out_srs=26910 --in_dir=laz --out_dir=out

#%%
from pathlib import Path
from shapely import Polygon

import argparse
import geopandas as gpd
import numpy as np
import pdal
import sys
#%%
def parse_arguments():
    '''parses the arguments, returns args'''
    # init parser
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--in_dir',
        type=str,
        required=False,
        help='Path to directory containing input las/z files'
    )

    parser.add_argument(
        '--out_dir',
        type=str,
        required=True,
        help='Path to directory where results will be written'
    )

    parser.add_argument(
        '--uri_list',
        type=str,
        required=False,
        help='Path to list of URIs where files are found. Can be URLs or local paths.'
    )

    parser.add_argument(
        '--buildings',
        type=str,
        required=True,
        help='Vector file of building footprints.'
    )

    parser.add_argument(
        '--aoi',
        type=str,
        required=False,
        help='Vector file of AOI. If --buildings extent is much larger than AOI, this will speed things up'
    )

    parser.add_argument(
        '--out_srs',
        type=int,
        required=False,
        help='Integer portion of EPSG code of desired output.'
    )

    # parse args
    args =  parser.parse_args()

    # make paths into full path objects
    if args.aoi is not None:
        args.aoi = Path(args.aoi).resolve()
    args.buildings = Path(args.buildings).resolve()
    if args.in_dir is not None:
        args.in_dir = Path(args.in_dir).resolve()
    if args.out_dir is not None:
        args.out_dir = Path(args.out_dir).resolve()

    return args

#%%
#uncomment below for testing or running in ipython
#ARGS=argparse.Namespace()
#ARGS.aoi = Path('../vectors/Eaton_Perimeter_20250121.geojson').resolve()
#ARGS.buildings = Path('../vectors/eaton_buildings.geojson').resolve()
#ARGS.out_srs = 26910
#ARGS.in_dir = Path('../laz').resolve()
#ARGS.out_dir = Path('../out').resolve()

ARGS = parse_arguments()

# read buildings (and AOI if need)
buildings = gpd.read_file(ARGS.buildings)
if ARGS.aoi is not None:
    aoi = gpd.read_file(ARGS.aoi)

# set crs for vectors (clip buildings to AOI if needed)
if ARGS.out_srs is not None:
    buildings = buildings.to_crs(epsg=ARGS.out_srs)
    if ARGS.aoi is not None:
        aoi = aoi.to_crs(epsg=ARGS.out_srs)
        buildings = gpd.clip(buildings, aoi)

# make a class column filled with 6
buildings['class'] = 6
# %%
# create stages and stage creator functions

def overlay_filter(vectors, layer):
    return pdal.Filter.overlay(
        column='class',
        datasource=vectors,
        layer=layer,
        dimension='Classification'
        )


expression = pdal.Filter.expression(expression='Classification == 6')

def writer(dst):
    return pdal.Writer.las(
        forward='all',
        filename=dst
        )

def pipeline(points, vectors, dst, layer):
    pipe = overlay_filter(vectors, layer).pipeline(points)
    pipe | expression
    pipe | writer(dst)

    return pipe
    

def get_pc_and_extent(laz):
    pipe = pdal.Reader.las(filename=laz).pipeline()
    pipe |= pdal.Filter.reprojection(out_srs=f'EPSG:{ARGS.out_srs}')
    p = pipe.execute()
    corners = [
        pipe.metadata['metadata']['readers.las'][corner]
        for corner
        in ['minx', 'maxx', 'miny','maxy']
    ]

    arr = pipe.arrays[0]
    minx = np.min(arr[0]['X'])
    maxx = np.max(arr[0]['X'])
    miny = np.min(arr[0]['Y'])
    maxy = np.max(arr[0]['Y'])

    return arr, Polygon((
        (minx, miny),
        (minx, maxy),
        (maxx, maxy),
        (maxx, miny),
        (minx, miny)
    )) 

def filter_points(arr, tile_buildings):
    ''''''


#%%

if ARGS.in_dir is not None:
    files = ARGS.in_dir.glob('*.laz')
elif ARGS.uri_list is not None:
    files = (Path(uri) for uri in ARGS.uri_list)
else:
    print(
        '''Yo fool! you either need to provide a directory containing
        las/las files, or a URI list!'''
        )
    sys.exit()

for src in files:
    print(src)
    # get points and extent
    points, extent = get_pc_and_extent(src)
    # save extent as geojson
    extent_path = Path(src.stem + '.geojson')
    layer = 'data'
    _ = gpd.clip(buildings, extent).to_file(extent_path,layer=layer)

    # run pipeline on points
    dst = ARGS.out_dir / (src.stem + f'_clipped_{ARGS.out_srs}.laz')
    pipe = pipeline(points, extent_path, dst, layer)
    n = pipe.execute()
    print(n)
# %%
