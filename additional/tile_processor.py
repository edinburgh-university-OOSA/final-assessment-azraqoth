# src/tile_processor.py
import os
import sys
import gc
import numpy as np
from scipy.ndimage import generic_filter
from pyproj import Transformer
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from processLVIS import lvisGround
from handleTiff import tiffHandle

# Class to handle DEM generation for a single tile
class TileProcessor:
    """
    Object-oriented handler for DEM tile processing and output.
    """
    def __init__(self, minX, maxX, minY, maxY, res, files, folder, output_dir, tile_id=None):
        self.minX = minX
        self.maxX = maxX
        self.minY = minY
        self.maxY = maxY
        self.res = res
        self.files = files
        self.folder = folder
        self.output_dir = output_dir
        self.tile_id = tile_id
        n_rows = int((maxY - minY) / res)
        n_cols = int((maxX - minX) / res)
        self.grid = np.full((n_rows, n_cols), -999.0, dtype=np.float32)
        self.t3031 = Transformer.from_crs("epsg:4326", "epsg:3031", always_xy=True)
        self.t4326 = Transformer.from_crs("epsg:3031", "epsg:4326", always_xy=True)

    # Process waveform data for this tile: subset data, estimate ground, and fill the elevation grid
    def process(self):
        geo_corners = [self.t4326.transform(x, y) for x, y in [
            (self.minX, self.minY), (self.maxX, self.minY),
            (self.minX, self.maxY), (self.maxX, self.maxY)
        ]]
        min_lon = min(c[0] for c in geo_corners)
        max_lon = max(c[0] for c in geo_corners)
        min_lat = min(c[1] for c in geo_corners)
        max_lat = max(c[1] for c in geo_corners)

        for f in tqdm(self.files, desc=f"Tile {self.tile_id}"):
            path = os.path.join(self.folder, f)
            lvis = lvisGround(path, setElev=True, minX=min_lon, maxX=max_lon, minY=min_lat, maxY=max_lat)
            if lvis.nWaves == 0:
                continue
            lvis.setElevations()
            lvis.estimateGround()
            valid = np.where(lvis.zG > -999)[0]
            if len(valid) == 0:
                continue
            x, y = self.t3031.transform(lvis.lon[valid], lvis.lat[valid])
            for i in range(len(x)):
                if not (self.minX <= x[i] < self.maxX and self.minY <= y[i] < self.maxY):
                    continue
                col = int((x[i] - self.minX) / self.res)
                row = int((self.maxY - y[i]) / self.res)
                if 0 <= row < self.grid.shape[0] and 0 <= col < self.grid.shape[1]:
                    self.grid[row, col] = lvis.zG[valid[i]]
            del lvis  # free waveform + z arrays
            gc.collect()

    # Fill missing data cells in the DEM grid using a 5x5 mean filter
    def fill_gaps(self):
        def filt(vals):
            v = vals[vals != -999]
            return np.mean(v) if len(v) else -999
        self.grid = generic_filter(self.grid, filt, size=5, mode='constant', cval=-999)

    # Save the processed tile as GeoTIFF; optionally append '_filled' if gap-filled
    def save(self, fill_suffix=False):
        os.makedirs(self.output_dir, exist_ok=True)
        suffix = "_filled" if fill_suffix else ""
        path = os.path.join(self.output_dir, f"tile_{self.tile_id}_{int(self.res)}m{suffix}.tif")
        tiff = tiffHandle(minX=self.minX, maxX=self.maxX, minY=self.minY, maxY=self.maxY, res=self.res)
        tiff.writeTiff(self.grid, filename=path, epsg=3031)
        return path
