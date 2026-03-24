#!/bin/bash

REPO="ShrabonDas/ulf-lib-python"
TAG="v0.1.0"
BASE_URL="https://github.com/$REPO/releases/download/$TAG"

FILES=("ulf_maps.json" "combine_features_cases.json")

for file in "${FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "Downloading $file..."
        curl -L -o "$file" "$BASE_URL/$file"
    else
        echo "$file already exists. skipping."
    fi
done

echo "Done."