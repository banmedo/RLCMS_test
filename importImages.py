# Author: Nishanta Khanal
# Date: 10th September 2018
#
# ----------------------------------------------------
#
# Script to facilitate importing of images
# pass year, season name, max cloud cover and roi

# import required libraries
import ee
from environment import environment

class importImages(object):

    def __init__(self):
        #initialize module
        ee.Initialize()
        self.env = environment()

    def runmodel(self):
        return


    # helper function to scale image
    def _scaleImage(self, imageCollection, thisScale):
        def __multiplyImage(image):
            return image.multiply(thisScale).copyProperties(image, image.propertyNames())

        return imageCollection.map(__multiplyImage)


    def getImagesInAYear(self, args):
        # year, season, maxCloudCover, roi, SLC
        if 'year' in args:
            year = args['year']
        else:
            print('Please specify a year')
            return ee.ImageCollection([])

        if 'region' in args:
            region = args['region']
        else:
            print('Please specify a region')
            return ee.ImageCollection([])

        if 'season' in args:
            season = args['season']
        else:
            season = self.env.defaults['season']

        if 'maxCloudCover' in args:
            maxCloudCover = args['maxCloudCover']
        else:
            maxCloudCover = self.env.defaults['maxCloudCover']

        if 'SLC' in args:
            # check whether to include landsat7 images or not
            #  as there is stripping error - starts at may 31, 2003(julian 151)
            SLC = args['SLC']
        else:
            SLC = self.env.defaults['SLC']

        # process start
        # check seasons
        # filter images
        # scale images
        # merge collections
        endyear = year
        if (season == 'drycool'):
            endyear += 1

        landsat5 = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR').filter(ee.Filter.calendarRange(year, endyear, 'year'))\
            .filter(ee.Filter.calendarRange(self.env.seasons[season][0], self.env.seasons[season][1], 'day_of_year'))\
            .filterBounds(region)\
            .filter(ee.Filter.lte('CLOUD_COVER', 30))\
            .select(self.env.commonBands['l5'], self.env.renameBands)

        landsat5 = self._scaleImage(landsat5, self.env.scale['l5']);

        landsat7 = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR').filter(ee.Filter.calendarRange(year, endyear, 'year'))\
            .filter(ee.Filter.calendarRange(self.env.seasons[season][0], self.env.seasons[season][1], 'day_of_year'))\
            .filterBounds(region)\
            .filter(ee.Filter.lte('CLOUD_COVER', 30))\
            .select(self.env.commonBands['l5'], self.env.renameBands)

        landsat7 = self._scaleImage(landsat7, self.env.scale['l7'])

        landsat8 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR').filter(ee.Filter.calendarRange(year, endyear, 'year'))\
            .filter(ee.Filter.calendarRange(self.env.seasons[season][0], self.env.seasons[season][1], 'day_of_year'))\
            .filterBounds(region)\
            .filter(ee.Filter.lte('CLOUD_COVER', 30))\
            .select(self.env.commonBands['l5'], self.env.renameBands)

        landsat8 = self._scaleImage(landsat8, self.env.scale['l8'])

        landsatMerged = landsat5
        if (SLC and year < 2004):
            landsatMerged = landsatMerged.merge(landsat7).merge(landsat8)
        else:
            landsatMerged = landsatMerged.merge(landsat8)

        # display the number of images found
        # print("Number of Images Found : ", landsatMerged.size().getInfo())
        return landsatMerged

    def getImagesInYearRange(self, args):
        if 'startyear' in args:
            startyear = args['startyear']
        else:
            print('Please specify a start year')
            return ee.ImageCollection([])

        if 'endyear' in args:
            endyear = args['endyear']
        else:
            print('Please specify a end year')
            return ee.ImageCollection([])

        if 'region' in args:
            region = args['region']
        else:
            print('Please specify a region')
            return ee.ImageCollection([])

        if 'season' in args:
            season = args['season']
        else:
            season = 'allyear'

        if 'maxCloudCover' in args:
            maxCloudCover = args['maxCloudCover']
        else:
            maxCloudCover = self.env.defaults['maxCloudCover']

        if 'SLC' in args:
            # check whether to include landsat7 images or not
            #  as there is stripping error - starts at may 31, 2003(julian 151)
            SLC = args['SLC']
        else:
            SLC = self.env.defaults['SLC']

        masterColl = ee.ImageCollection([])
        for year in range(startyear,endyear):
            imgColl = self.getImagesInAYear({'year':year,'region':region,'season':season,'SLC':SLC,'maxCloudCover':maxCloudCover})
            masterColl = masterColl.merge(imgColl)

        return masterColl

if (__name__ == '__main__'):
    importImg = importImages()
    envs = environment()
    importImg.getImagesInAYear({'year':2010, 'region':envs.testRegion})

# getImages({year: 2010, season: 'drycool', maxCloudCover: 30, region: region, SLC: false});