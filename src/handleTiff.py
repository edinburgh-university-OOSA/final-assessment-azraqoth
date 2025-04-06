

'''
A class to handle geotiffs
'''

#######################################################
# import necessary packages

from pyproj import Proj, transform # package for reprojecting data
from osgeo import gdal             # package for handling geotiff data
from osgeo import osr              # package for handling projection information
import numpy as np

#######################################################

class tiffHandle():
  '''
  Class to handle geotiff files
  '''

  ########################################

  def __init__(self, filename=None, minX=None, maxX=None, minY=None, maxY=None, res=None, data=None, epsg=3031):
    self.filename = filename
    self.minX = minX
    self.maxX = maxX
    self.minY = minY
    self.maxY = maxY
    self.res = res
    self.epsg = epsg
    self.data = data
    self.nX = None
    self.nY = None

    # Calculate grid size if possible
    if all(v is not None for v in [minX, maxX, minY, maxY, res]):
        if maxX > minX and maxY > minY and res > 0:
            self.nX = int((maxX - minX) / res)
            self.nY = int((maxY - minY) / res)
        else:
            raise ValueError("Invalid bounds or resolution: check that max > min and res > 0")
    else:
        self.nX = None
        self.nY = None
  

  ########################################

  def writeTiff(self,data,filename="dem_image.tif",epsg=4326):
    '''
    Write a geotiff from a raster layer
    '''

    # set geolocation information (note geotiffs count down from top edge in Y)
    geotransform = (self.minX, self.res, 0, self.maxY, 0, -1*self.res)

    # load data in to geotiff object
    dst_ds = gdal.GetDriverByName('GTiff').Create(filename, self.nX, self.nY, 1, gdal.GDT_Float32)

    dst_ds.SetGeoTransform(geotransform)    # specify coords
    srs = osr.SpatialReference()            # establish encoding
    srs.ImportFromEPSG(epsg)                # WGS84 lat/long
    dst_ds.SetProjection(srs.ExportToWkt()) # export coords to file
    dst_ds.GetRasterBand(1).WriteArray(data)  # write image to the raster
    dst_ds.GetRasterBand(1).SetNoDataValue(-999)  # set no data value
    dst_ds.FlushCache()                     # write to disk
    dst_ds = None

    print("Image written to",filename)
    return


  ########################################

  def readTiff(self, filename):
    '''
    Read a geotiff into RAM
    '''
    ds = gdal.Open(filename)
    self.nX = ds.RasterXSize
    self.nY = ds.RasterYSize

    transform_ds = ds.GetGeoTransform()
    self.minX = transform_ds[0]
    self.res = transform_ds[1]
    self.maxY = transform_ds[3]
    self.maxX = self.minX + self.nX * self.res
    self.minY = self.maxY + self.nY * transform_ds[5]

    self.data = ds.GetRasterBand(1).ReadAsArray(0, 0, self.nX, self.nY)


#######################################################

