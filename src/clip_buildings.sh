#!/bin/sh

RM=do_not_remove
AG=do_not_remove

while getopts "hr:u:o:c:" flag; do
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
        echo "        -r - If set original las/laz files will be deleted after new"
        echo "        files are written. NOT RECOMMENDED if disk hard drive space"
        echo "        is sufficient to hold both copies at once."
        echo "        "        
        echo "     arguments:"
        echo "        -u [list_of_uris] - This can be either a list of uris to"
        echo "         point clouds, one per line, OR a single line with the path to"
        echo "         a directory containing the las/laz files."
        echo "        "
        echo "        -o [output_dir] - Path to directory where clipped point"
        echo "         clouds will be written."
        echo "        "
        echo "        -c [clip_polygons] - OGR readable polygon layer.  Points"
        echo "        lying within polygons will be removed."
        exit 0
        ;;
    r)  RM=rm;;
    u)  INPUT=$OPTARG;;
    o)  OUTDIR=$OPTARG;;   
    c)  CLIP=$OPTARG;; 
esac
done


SRS=26910

# make sure clip is passed,make cls column containing 6 for buildings
#if [[ -f CLIP ]]; then
    rm -f cls.json
    python -c "import geopandas as gpd; df = gpd.read_file('$CLIP'); df['CLS'] = 6; df.to_crs(epsg=$SRS).to_file('cls.geojson')"
#else
#    echo "It seems that $CLIP [clipping vector] is not a file."
#    exit 1
#fi

# make pipeline
cat > pipeline.json <<'EOF'
    [
        {
            "tag" : "read",
            "type" : "readers.las"
        },
        {
            "tag": "ovrly",
            "column": "CLS",
            "datasource": "Placeholder.geojson",
            "dimension": "Classification",
            "type": "filters.overlay"
        },
        {
            "tag": "exp",
            "expression": "Classification == 6",
            "type": "filters.expression"
        },
        {
            "tag": "wrt",
            "type": "writers.las",
            "filename": "placeholder.laz",
            "forward": "all"
        }
    ]
EOF

# check other args, run pipeline in ||
if [[ -v INPUT ]]; then
    if [[ -v OUTDIR ]]; then
        if [ -d $OUTDIR ]; then
            echo "Files will be written to $OUTDIR."
        else
            echo "$OUTDIR is not a directory! Specify a valid write directory!"
            exit 1
        fi
        # see if input is list or path to dir, act accordingly
        if [ -d $INPUT ]; then
            ls $INPUT | parallel --progress  \
                "pdal translate $INPUT/{} \
                $OUTDIR/{/.}_tmp.laz filters.reprojection \
                --filters.reprojection.out_srs='EPSG:$SRS' \
                && \
                ogr2ogr $OUTDIR/{/.}_tmp.geojson cls.geojson \
                -sql \"SELECT * FROM input WHERE ST_Within(geometry, ST_GeomFromText($(pdal info $OUTDIR/{/.}_tmp.laz --boundary | jq -r .boundary.boundary), 26910))\" \
                && \
                pdal pipeline pipeline.json \
                --stage.read.filename=$OUTDIR/{/.}_tmp.laz \
                --stage.wrt.filename=$OUTDIR/{/.}_clipped_$SRS.laz
                --stage.ovrly.datasource=$OUTDIR/{/.}_tmp.geojson \
                && \
                rm $OUTDIR/{/.}_tmp.*"


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