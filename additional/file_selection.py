"""
Check which LVIS .h5 files intersect a fixed AOI.
Save the intersecting filenames to valid_xxxx_files.txt.
"""

import os
import sys
import argparse
import shapely.ops
import fiona
from shapely.geometry import box, shape

# Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from processLVIS import lvisGround

def load_aoi_polygon():
    # Load the area of interest from geojson file
    geojson_path = os.path.join(os.path.dirname(__file__), "..", "data", "bound2.geojson")
    with fiona.open(geojson_path, 'r') as f:
        shapes = [shape(feature['geometry']) for feature in f]
    # Combine all shapes into one polygon
    return shapely.ops.unary_union(shapes)

def main():
    # Setup command line argument parser
    parser = argparse.ArgumentParser(description="Check which LVIS .h5 files intersect bound2.geojson AOI.")
    parser.add_argument("--folder", required=True, help="Folder containing LVIS .h5 files")
    args = parser.parse_args()

    folder = args.folder

    print(f"\n📍 Loading AOI from: bound2.geojson")
    aoi_polygon = load_aoi_polygon()
    print("✅ AOI loaded.\n")

    valid_files = []

    # Check each .h5 file against the AOI
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".h5"):
            full_path = os.path.join(folder, fname)
            try:
                # Load only the bounds to save memory
                lvis = lvisGround(full_path, onlyBounds=True)
                bounds = lvis.bounds

                # Fix longitude values that cross the antimeridian
                if bounds[0] > 180:
                    bounds[0] -= 360
                    bounds[2] -= 360

                # Create a bounding box for the file
                file_box = box(bounds[0], bounds[1], bounds[2], bounds[3])

                # Check for intersection with the AOI
                if file_box.intersects(aoi_polygon):
                    print(f"✅ {fname} intersects AOI")
                    valid_files.append(fname)
                else:
                    print(f"❌ {fname} does NOT intersect AOI")

            except Exception as e:
                print(f"⚠️  Error reading {fname}: {e}")

    # Extract year from folder path
    year = ''.join(filter(str.isdigit, os.path.basename(folder)))
    output_filename = f"valid_{year}_files.txt" if year else "valid_files.txt"

    # Save list of valid files to text file
    with open(output_filename, "w") as f:
        for fname in valid_files:
            f.write(fname + "\n")

    print(f"\n📝 Saved {len(valid_files)} valid files to {output_filename}")

if __name__ == "__main__":
    main()