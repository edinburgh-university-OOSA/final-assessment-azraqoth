
'''
Some example functions for processing LVIS data
'''

#######################################

import numpy as np
from lvisClass import lvisData
from pyproj import Transformer
from scipy.ndimage.filters import gaussian_filter1d 


#######################################

class lvisGround(lvisData):
    
    def __init__(self, filename, setElev=True, minX=-1e10, maxX=1e10, minY=-1e10, maxY=1e10, onlyBounds=False):
      super().__init__(filename, setElev=setElev, minX=minX, maxX=maxX, minY=minY, maxY=maxY, onlyBounds=onlyBounds)

      # Only reproject if lon/lat exist (i.e., data was found)
      if hasattr(self, "lon") and hasattr(self, "lat") and self.lon is not None:
          transformer = Transformer.from_crs("epsg:4326", "epsg:3031", always_xy=True)
          self.x, self.y = transformer.transform(self.lon, self.lat)
      else:
          self.x = self.y = None  # fallback

  
    def estimateGround(self,threshScale=5,statsLen=10,minWidth=3,smooWidth=0.5):
      '''
      Processes waveforms to estimate ground
      Only works for bare Earth. DO NOT USE IN TREES
      '''
      # find noise statistics
      self.findStats(statsLen=statsLen)

      # set threshold
      threshold=self.setThreshold(threshScale)

      # remove background
      self.denoise(threshold,minWidth=minWidth,smooWidth=smooWidth)

      # find centre of gravity of remaining signal
      self.CofG()


    #######################################################

    def setThreshold(self,threshScale):
      '''
      Set a noise threshold
      '''
      threshold=self.meanNoise+threshScale*self.stdevNoise
      return(threshold)


    #######################################################

    def CofG(self):
      '''
      Find centre of gravity of denoised waveforms
      '''
      # allocate space for ground elevation
      self.zG = np.full(self.nWaves, -999.9, dtype=np.float32)  # no data flag for now
      
      # loop over waveforms
      for i in range(0,self.nWaves):
        if(np.sum(self.denoised[i])>0.0):   # avoid empty waveforms (clouds etc)
          self.zG[i]=np.average(self.z[i],weights=self.denoised[i])  # centre of gravity


    #######################################################


    def reproject(self, inEPSG, outEPSG):
      '''
      Reproject footprint coordinates using pyproj.Transformer
      '''
      transformer = Transformer.from_crs(inEPSG, outEPSG, always_xy=True)
      self.lon, self.lat = transformer.transform(self.lon, self.lat)



    ##############################################

    def findStats(self,statsLen=10):
      '''
      Finds standard deviation and mean of noise
      '''

      # make empty arrays
      self.meanNoise=np.empty(self.nWaves)
      self.stdevNoise=np.empty(self.nWaves)

      # determine number of bins to calculate stats over
      res=(self.z[0,0]-self.z[0,-1])/self.nBins    # range resolution
      noiseBins=int(statsLen/res)   # number of bins within "statsLen"

      # loop over waveforms
      for i in range(0,self.nWaves):
        self.meanNoise[i]=np.mean(self.waves[i,0:noiseBins])
        self.stdevNoise[i]=np.std(self.waves[i,0:noiseBins])


    ##############################################

    def denoise(self,threshold,smooWidth=0.5,minWidth=3):
      '''
      Denoise waveform data
      '''

      # find resolution
      res=(self.z[0,0]-self.z[0,-1])/self.nBins    # range resolution

      # make array for output
      self.denoised = np.zeros((self.nWaves, self.nBins), dtype=np.float32)

      # loop over waves
      for i in range(0,self.nWaves):
        #print("Denoising wave",i+1,"of",self.nWaves)

        # subtract mean background noise
        self.denoised[i]=self.waves[i]-self.meanNoise[i]

        # set all values less than threshold to zero
        self.denoised[i,self.denoised[i]<threshold[i]]=0.0

        # minimum acceptable width
        binList=np.where(self.denoised[i]>0.0)[0]
        for j in range(0,binList.shape[0]):       # loop over waveforms
          if((j>0)&(j<(binList.shape[0]-1))):    # are we in the middle of the array?
            if((binList[j]!=binList[j-1]+1)|(binList[j]!=binList[j+1]-1)):  # are the bins consecutive?
              self.denoised[i,binList[j]]=0.0   # if not, set to zero

        # smooth
        self.denoised[i]=gaussian_filter1d(self.denoised[i],smooWidth/res)


#############################################################

