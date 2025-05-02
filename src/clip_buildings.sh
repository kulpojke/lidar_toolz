#!/bin/sh
# bash clip_buildings.sh -i ../laz -o ../out -c ../vectors/eaton_buildings.geojson -s 26910

RM=do_not_remove
AG=do_not_remove

while getopts "hi:o:c:s:" flag; do
case "$flag" in
    h)  
        echo "SYNOPSIS"  
        echo "     ./start [options] -k key_file -u list_of_urls -o output_dir -b bucket -d bucket_dir "
        echo "DESCRIPTION"
        echo "     Removes points lying within polygons (e.g. building footprints)"
        echo "     from point clouds.  Point Clouds and Vectors must be in the same srs"
        echo "     Copies them to gcloud bucket"
        echo "        "
        echo "     options:"
        echo "        "
        echo "        -h - Display help"
        echo "        "        
        echo "     arguments:"
        echo "        -i [input_dir] - Path to input directory"
        echo "        -o [output_dir] - Path to directory where clipped point"
        echo "         clouds will be written."
        echo "        "
        echo "        -c [clip_polygons] - OGR readable polygon layer.  Points"
        echo "        lying within polygons will be removed."
        echo "        -s [srs] - srs as numerical portion of EPSG code,"
        echo "        e.g. 26910 (for EPSG:26910)"
        exit 0
        ;;
    i)  INPUT=$OPTARG;;
    o)  OUTDIR=$OPTARG;;   
    c)  CLIP=$OPTARG;;
    s)  SRS=$OPTARG;; 
esac
done

TMPDIR=temporary_directory
mkdir -p $TMPDIR

# check other args, run pipeline in ||
if [[ -v INPUT ]]; then
    if [[ -v OUTDIR ]]; then
        # see if input is list or path to dir, act accordingly
        if [ -d $INPUT ]; then
            ls $INPUT | parallel --progress  \
                "pdal translate $INPUT/{} $TMPDIR/{} \
                    filters.reprojection \
                    --filters.reprojection.out_srs=EPSG:$SRS \
                && \
                python extent_and_json.py \
                    --in_laz=$TMPDIR/{} \
                    --out_dir=$OUTDIR \
                    --buildings=$CLIP \
                    --tmp_dir=$TMPDIR \
                    --out_srs=$SRS \
                && \
                pdal pipeline $TMPDIR/{.}.json"

        elif [ -f $INPUT]; then
            cat $INPUT | parallel 'echo {}'    
        else
            echo "its a list"
        fi
    else
      echo "You must pass a value after -o"
    fi
else
      echo "You must pass a value after -u"
fi