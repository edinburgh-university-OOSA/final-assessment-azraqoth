import os
import numpy as np
import sys
from scipy.ndimage import generic_filter
from pyproj import Transformer
from tqdm import tqdm
from osgeo import gdal

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from processLVIS import lvisGround
from handleTiff import tiffHandle

def read_valid_files(filepath, test_files=None):
    """
    Read valid filenames from a text file. Optionally filter using test_files list.
    """
    # Read file paths line by line
    with open(filepath, 'r') as f:
        files = [line.strip() for line in f if line.strip()]
    # Filter by test files if provided
    if test_files:
        return [f for f in files if f in test_files]
    return files

def get_all_bounds(valid_files, folder):
    """
    Compute the full bounding box across all LVIS files, transformed into EPSG:3031.
    Adds a 5% buffer to ensure full spatial coverage.
    """
    # Initialize with extreme values
    overall_minX = float('inf')
    overall_maxX = float('-inf')
    overall_minY = float('inf')
    overall_maxY = float('-inf')

    # Check each file's bounds
    for filename in tqdm(valid_files, desc="Analyzing files"):
        path = os.path.join(folder, filename)
        lvis = lvisGround(path, onlyBounds=True)
        if not hasattr(lvis, 'bounds'):
            continue
        min_lon, min_lat, max_lon, max_lat = lvis.bounds
        
        # Transform from WGS84 to EPSG3031
        transformer = Transformer.from_crs("epsg:4326", "epsg:3031", always_xy=True)
        
        # Check all corners of the bounding box
        corners = [(min_lon, min_lat), (max_lon, min_lat), (min_lon, max_lat), (max_lon, max_lat)]
        for lon, lat in corners:
            x, y = transformer.transform(lon, lat)
            overall_minX = min(overall_minX, x)
            overall_maxX = max(overall_maxX, x)
            overall_minY = min(overall_minY, y)
            overall_maxY = max(overall_maxY, y)

    # Add 5% buffer to bounds
    width = overall_maxX - overall_minX
    height = overall_maxY - overall_minY
    buffer_x = width * 0.05
    buffer_y = height * 0.05
    return (
        overall_minX - buffer_x,
        overall_maxX + buffer_x,
        overall_minY - buffer_y,
        overall_maxY + buffer_y
    )

def generate_tiles(bounds, tiles):
    """
    Divide the full bounding box into NxN tile bounds.
    """
    # Extract bounds and calculate tile dimensions
    minX, maxX, minY, maxY = bounds
    tile_w = (maxX - minX) / tiles
    tile_h = (maxY - minY) / tiles
    
    # Create a grid of tile extents
    out = []
    for i in range(tiles):
        for j in range(tiles):
            out.append((minX + i * tile_w, minX + (i + 1) * tile_w,
                        minY + j * tile_h, minY + (j + 1) * tile_h))
    return out

def merge_tiles(paths, output, output_dir):
    """
    Merge individual tile GeoTIFFs into a single raster using GDAL VRT.
    """
    # Create a VRT from multiple tiles
    vrt = os.path.join(output_dir, "merged_temp.vrt")
    vrt_opts = gdal.BuildVRTOptions(resampleAlg='nearest', addAlpha=False)
    gdal.BuildVRT(vrt, paths, options=vrt_opts)
    
    # Convert VRT to compressed GeoTIFF
    t_opts = gdal.TranslateOptions(format='GTiff', creationOptions=['COMPRESS=LZW', 'TILED=YES'], noData=-999)
    gdal.Translate(output, vrt, options=t_opts)
    
    # Clean up temporary file
    os.remove(vrt)
    return output

def fill_gaps_in_tile(path):
    """
    Fills gaps in a single tile (where value == -999) using a 5x5 mean filter.
    """
    # Read the GeoTIFF file
    t = tiffHandle()
    t.readTiff(path)
    
    # Define filter function
    def filt(vals):
        v = vals[vals != -999]
        return np.mean(v) if len(v) else -999
    
    # Apply mean filter to fill gaps
    filled = generic_filter(t.data, filt, size=5, mode='constant', cval=-999)
    
    # Save result to a new file
    filled_path = path.replace('.tif', '_filled.tif')
    t.writeTiff(filled, filename=filled_path, epsg=3031)
    return filled_path