#! /bin/sh

die () {
    exitcode="$1"; shift
    echo $*
    exit $exitcode
}

if [ -z "$URIPREFIX" ]; then
    test \! -z "$RADIX_PUBLIC_DOMAIN_NAME"  || die 1 "Unable to build PREFIX."
    URIPREFIX="https://${RADIX_PUBLIC_DOMAIN_NAME}"
fi

echo "URIPREFIX=$URIPREFIX"

test -d ./definitions || die 1 "Definitions not found."

mkdir schemas || die 1 "Unable to create directory 'schemas'."

find ./definitions -type d -name schema -print | \
    while read dir; do
        pdir=`dirname "$dir"`
        sdir=schemas/`basename "$pdir"`
        mkdir "$sdir"
        find "$dir" -maxdepth 1 -name '*.json' -print | \
            while read file; do
                #echo "file: $file"
                ffile=`basename "$file"`
                id=`echo "$URIPREFIX"/"$sdir"/"$ffile" | sed -e 's/ /%20/g'`
                #echo "id: $id"
                #echo "creating $sdir/$ffile"
                cat "$file" | jq '.["$id"]='\""$id"\" > "$sdir"/"$ffile"
            done
    done


