import numpy as np
import argparse
import glob
import os
import sys
# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from handleTiff import tiffHandle

def calculate_volume_change_overlap(dem_2009_path, dem_2015_path, output_diff_path):
    # Load DEMs from file paths
    dem_2009 = tiffHandle()
    dem_2009.readTiff(dem_2009_path)

    dem_2015 = tiffHandle()
    dem_2015.readTiff(dem_2015_path)

    # Check that DEMs have the same resolution
    assert np.isclose(dem_2009.res, dem_2015.res), f"DEM resolutions do not match: {dem_2009.res} vs {dem_2015.res}"
    res = dem_2009.res

    # Find where the two DEMs overlap
    minX = max(dem_2009.minX, dem_2015.minX)
    maxX = min(dem_2009.maxX, dem_2015.maxX)
    minY = max(dem_2009.minY, dem_2015.minY)
    maxY = min(dem_2009.maxY, dem_2015.maxY)

    # Make sure there is some overlap
    if minX >= maxX or minY >= maxY:
        raise ValueError("No overlapping area between DEMs")

    # Helper function to convert real-world coordinates to pixel indices
    def crop_indices(dem, minX, maxX, minY, maxY):
        x0 = int((minX - dem.minX) / res)
        x1 = int((maxX - dem.minX) / res)
        y0 = int((dem.maxY - maxY) / res)
        y1 = int((dem.maxY - minY) / res)
        return x0, x1, y0, y1

    # Calculate pixel indices for both DEMs
    x0_2009, x1_2009, y0_2009, y1_2009 = crop_indices(dem_2009, minX, maxX, minY, maxY)
    x0_2015, x1_2015, y0_2015, y1_2015 = crop_indices(dem_2015, minX, maxX, minY, maxY)

    # Extract the overlapping regions
    crop_2009 = dem_2009.data[y0_2009:y1_2009, x0_2009:x1_2009]
    crop_2015 = dem_2015.data[y0_2015:y1_2015, x0_2015:x1_2015]

    # Calculate elevation change (2015 minus 2009)
    change = crop_2015 - crop_2009
    
    # Create mask for no-data values
    mask = (crop_2009 == -999) | (crop_2015 == -999)
    change[mask] = -999

    # Save the elevation change to a new GeoTIFF
    out = tiffHandle(
        minX=minX,
        maxX=maxX,
        minY=minY,
        maxY=maxY,
        res=res
    )
    out.writeTiff(change, filename=output_diff_path, epsg=3031)

    # Calculate total volume change in cubic meters
    pixel_area = res ** 2
    volume_change = np.sum(change[~mask]) * pixel_area

    print("✅ Volume change in m³ over overlapping area:", volume_change)
    return volume_change


def find_dem_files(folder_path):
    # Find 2009 DEM files based on filename pattern
    dem_2009_list = glob.glob(os.path.join(folder_path, "*merged*2009*.tif"))

    # Find 2015 DEM files based on filename pattern
    dem_2015_list = glob.glob(os.path.join(folder_path, "*merged*2015*.tif"))

    # Make sure we found at least one file for each year
    if not dem_2009_list or not dem_2015_list:
        raise FileNotFoundError("❌ Could not find both 2009 and 2015 DEMs with 'merged' in the filename.")

    # Return the first matching file for each year
    return dem_2009_list[0], dem_2015_list[0]



if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Task 5: Calculate elevation and volume change using overlapping DEMs.")
    parser.add_argument("--folder", type=str, required=True, help="Folder containing the merge DEMs")
    parser.add_argument("--output_diff", type=str, required=True, help="Output GeoTIFF path for elevation change")

    args = parser.parse_args()

    # Find DEM files
    dem_2009, dem_2015 = find_dem_files(args.folder)
    print("🔍 Found 2009 DEM:", dem_2009)
    print("🔍 Found 2015 DEM:", dem_2015)

    # Calculate volume change and save difference map
    calculate_volume_change_overlap(dem_2009, dem_2015, args.output_diff)