#!/bin/sh

schemas_dir=schemas

die () {
    exitcode="$1"; shift
    echo $*
    exit $exitcode
}

test -d $schemas_dir || die 1 "Schemas not found."

if [ -z "$URIPREFIX" ]; then
    test \! -z "$RADIX_PUBLIC_DOMAIN_NAME"  || die 1 "Unable to build PREFIX."
    URIPREFIX="https://${RADIX_PUBLIC_DOMAIN_NAME}"
fi

echo "Using URIPREFIX=$URIPREFIX ..."

find "$schemas_dir" -type f -name '*.json' | while read -r file; do
    tmp_file=$(mktemp)

    id=`echo "$URIPREFIX"/"$file" | sed -e 's/ /%20/g'`
    # Replace $id to temp file and write it over the original
    if jq '.["$id"] = "'$id'"' "$file" > "$tmp_file"; then
        echo "$file -> \"\$id\": \"$id\""
        mv "$tmp_file" "$file"
    else
        rm "$tmp_file" || die 1 "Failed to process $file"
    fi
done

echo "Done."
