import ee

class environment(object):
    def __init__(self):

        #export params
        self.collFolder = 'projects/servir-hkh/nk-comp/'
        self.exportScale = 30

        # setting up variables
        self.seasons = {
            'allyear': [1,365],
            'drycool': [305, 59],
            'dryhot': [60, 181],
            'rainy': [182, 304]
        }

        self.defaults = {
            'maxCloudCover': 90,
            'season': 'drycool',
            'SLC': True
        }

        # setting parameters
        self.commonBands = {
            'l5': ee.List([0, 1, 2, 3, 4, 5, 6, 9, 7]),
            'l7': ee.List([0, 1, 2, 3, 4, 5, 6, 9, 7]),
            'l8': ee.List([1, 2, 3, 4, 5, 6, 7, 10, 9])
        }

        # new names for the bands
        self.renameBands = ee.List(['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'temp', 'pixel_qa', 'sr_atmos']);

        # scale for the image bands
        self.scale = {
            'l5': [0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.1, 1, 0.001],
            'l7': [0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.1, 1, 0.001],
            'l8': [0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.1, 1, 1],
        }

        self.testRegion = ee.Geometry.Polygon(
        [[[84.21505058389494, 27.855485565759306],
          [84.55048295546044, 27.533476511571877],
          [84.94538761649255, 27.720661315751688],
          [84.6008138081761, 28.087103456548363]]])


        #parameters for cloud bursting
        self.cloudValue = 32
        self.shadowValue = 8
        self.snowValue = 16

        # cloudScoreThresh: If using the cloudScoreTDOMShift method - Threshold for cloud
        # masking(lower number masks more clouds.Between 10 and 30 generally
        #  works best)

        self.zScoreThresh = -1
        self.shadowSumThresh = 0.35
        self.cloudScoreThresh = 20
        self.cloudScorePctl = 0
        self.contractPixels = 1.5
        self.dilatePixels = 2.5

        # parameters for brdf
        self.PI = ee.Number(3.14159265359)
        self.MAX_SATELLITE_ZENITH = 7.5
        self.MAX_DISTANCE = 1000000
        self.UPPER_LEFT = 0
        self.LOWER_LEFT = 1
        self.LOWER_RIGHT = 2
        self.UPPER_RIGHT = 3

        # parameters for terrain correction
        self.terrainScale = 300

        self.demID = 'CGIAR/SRTM90_V4'
        self.dem30m = 'USGS/SRTMGL1_003'

        self.degree2radian = 0.01745

        #parameters for compositing
        self.medoidIncludeBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
        self.medianIncludeBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
        self.stdevIncludeBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
