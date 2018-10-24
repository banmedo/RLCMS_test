import ee
from importImages import importImages
from environment import environment

class cloudBurst(object):

    def __init__(self):
        ee.Initialize()
        self.envs = environment()

        # cloudScoreThresh: If using the cloudScoreTDOMShift method - Threshold for cloud
        # masking(lower number masks more clouds.Between 10 and 30 generally
        #  works best)

    # helper function to apply an expression and linearly rescale the output.
    # Used in the sentinelCloudScore function below.
    def _rescale(self, img, exp, thresholds):
        return img.expression(exp, {'img': img})\
            .subtract(thresholds[0]).divide(thresholds[1] - thresholds[0]);

    def _cloudMask(self, img):
        cloud = img.select('pixel_qa').bitwiseAnd(self.envs.cloudValue).neq(0)
        cloud_shadow = img.select('pixel_qa').bitwiseAnd(self.envs.shadowValue).neq(0)
        return img.updateMask(cloud.Or(cloud_shadow).Not())

    def _snowMaskQA(self, img):
        snow = img.select('pixel_qa').bitwiseAnd(self.envs.snowValue)
        return snow
        # return img.updateMask(snow)

    def _landsatCloudScoreMask(self, img):

        # compute several indicators of cloudiness and take the minimum of them
        score = ee.Image(1.0)
        # clouds are reasonably bright in the blue band
        score = score.min(self._rescale(img,'img.blue', [0.1, 0.3]))
        # clouds are reasonably bright in all visible bands
        score = score.min(self._rescale(img, 'img.red + img.green + img.blue', [0.2, 0.8]))
        # clouds are reasonably bright in al infrared bands
        score = score.min(self._rescale(img, 'img.nir + img.swir1 + img.swir2', [0.3, 0.8]))
        # clouds are reasonably cool in temperature
        score = score.min(self._rescale(img, 'img.temp', [300, 290]))
        #however clouds are not snow
        ndsi = img.normalizedDifference(['green', 'swir1'])
        score = score.min(self._rescale(ndsi, 'img', [0.8, 0.6]))

        score = score.multiply(100).byte()
        score = score.clamp(0, 100)
        cloudMask = score.lt(self.envs.cloudScoreThresh).focal_max(self.envs.contractPixels).focal_min(self.envs.dilatePixels).rename('cloudMask')
        newImg = img.updateMask(cloudMask)
        snow = self._snowMaskQA(img)
        return newImg.unmask(snow).addBands(cloudMask).addBands(score.rename(['cloudScore'])).copyProperties(img, img.propertyNames())

    def _shadowMask(self, collection, studyArea):
        shadowSumBands  = ['nir', 'swir1']

        # allCollection = importImages().getImagesInYearRange({'startyear':2000,'endyear':2001,'region':studyArea})\
        #     .select(shadowSumBands)
        # allCollection = collection
        # Get some pixel - wise stats for the time series
        # irStdDev = allCollection.select(shadowSumBands).reduce(ee.Reducer.stdDev())
        # irMean = allCollection.select(shadowSumBands).mean()

        LTA = ee.Image(self.envs.LTAimageId).divide(10000);
        irStdDev = LTA.select(['nir_stdDev', 'swir1_stdDev'], ['nir', 'swir1']);
        irMean = LTA.select(['nir', 'swir1'])

        def maskDarkOutliers(img):
            zScore = img.select(shadowSumBands).subtract(irMean).divide(irStdDev)
            irSum = img.select(shadowSumBands).reduce(ee.Reducer.sum())
            TDOMMask = zScore.lt(self.envs.zScoreThresh).reduce(ee.Reducer.sum()).eq(2).And (irSum.lt(self.envs.shadowSumThresh))
            TDOMMask = TDOMMask.focal_min(self.envs.contractPixels).focal_max(self.envs.dilatePixels).rename('TDOMMask')
            return img.updateMask(TDOMMask.Not()).addBands(TDOMMask)

        collection = collection.map(maskDarkOutliers)
        return collection

    def runModel(self, imageCollection, region):
        imageCollection = imageCollection.map(self._landsatCloudScoreMask)
        imageCollection = imageCollection.map(self._cloudMask)
        imageCollection = self._shadowMask(imageCollection, region)
        print("Process Update: Clouds and Shadows removed!", imageCollection.size().getInfo())
        return imageCollection