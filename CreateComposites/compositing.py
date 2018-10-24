import ee
from environment import environment

class createComposite(object):

    def __init__(self):
        ee.Initialize()
        self.envs = environment()

    def getMedoidAndStdevs(self, collection):
        medoidIncludeBands = self.envs.medoidIncludeBands
        stdevIncludeBands = self.envs.stdevIncludeBands
        otherIncludeBands = self.envs.otherIncludeBands
        # Find band names in first image
        f = ee.Image(collection.first())
        bandNames = f.bandNames()

        # Find the median
        median = collection.select(medoidIncludeBands).median()

        medBandList = median.bandNames()

        medBandNumbers = ee.List.sequence(1, medBandList.length())

        # otherBands = bandNames.removeAll(medoidIncludeBands)

        others = collection.select(otherIncludeBands).mean()

        # Find the squared difference from the median for each image
        def findMedianDistance(img):
            diff = ee.Image(img).select(medoidIncludeBands).subtract(median).pow(ee.Image.constant(2))
            return diff.reduce('sum').addBands(img)

        medianDistance = collection.map(findMedianDistance)

        # Minimize the distance across all bands
        medoid = ee.ImageCollection(medianDistance).reduce(ee.Reducer.min(bandNames.length().add(1))).select(medBandNumbers,
                                                                                                     medBandList)

        # select bands to compute standard deviation
        selectedCollection = collection.select(stdevIncludeBands)

        # mapping function to add normalized difference
        def addNormalizedDifferences(image):
            image = image.addBands(image.normalizedDifference(['nir', 'swir2']).rename('ND_nir_swir2'))
            image = image.addBands(image.normalizedDifference(['green', 'swir1']).rename('ND_green_swir1'))
            image = image.addBands(image.normalizedDifference(['nir', 'red']).rename('ND_nir_red'))
            return image

        # add ND indices
        selectedCollection = selectedCollection.map(addNormalizedDifferences)

        #now compute standard deviation
        stdevImage = selectedCollection.reduce(ee.Reducer.stdDev())

        print("Process Update: Medoid calculated complete!")
        return medoid.addBands(others).addBands(stdevImage)

    def getMedoidAndPercentiles(self, collection):
        medoidIncludeBands = self.envs.medoidIncludeBands
        stdevIncludeBands = self.envs.stdevIncludeBands
        otherIncludeBands = self.envs.otherIncludeBands
        # Find band names in first image
        f = ee.Image(collection.first())
        bandNames = f.bandNames()

        # Find the median
        median = collection.select(medoidIncludeBands).median()

        medBandList = median.bandNames()

        medBandNumbers = ee.List.sequence(1, medBandList.length())

        # otherBands = bandNames.removeAll(medoidIncludeBands)

        others = collection.select(otherIncludeBands).mean()

        # Find the squared difference from the median for each image
        def findMedianDistance(img):
            diff = ee.Image(img).select(medoidIncludeBands).subtract(median).pow(ee.Image.constant(2))
            return diff.reduce('sum').addBands(img)

        medianDistance = collection.map(findMedianDistance)

        # Minimize the distance across all bands
        medoid = ee.ImageCollection(medianDistance).reduce(ee.Reducer.min(bandNames.length().add(1))).select(medBandNumbers,
                                                                                                     medBandList)

        # select bands to compute standard deviation
        selectedCollection = collection.select(stdevIncludeBands)

        # mapping function to add normalized difference
        def addNormalizedDifferences(image):
            image = image.addBands(image.normalizedDifference(['nir', 'swir2']).rename('ND_nir_swir2'))
            image = image.addBands(image.normalizedDifference(['green', 'swir1']).rename('ND_green_swir1'))
            image = image.addBands(image.normalizedDifference(['nir', 'red']).rename('ND_nir_red'))
            return image

        # add ND indices
        selectedCollection = selectedCollection.map(addNormalizedDifferences)

        # compute value closest to percentiles
        medoidDown = self.medoidMosaicPercentiles(selectedCollection, self.envs.percentiles[0])
        medoidUp = self.medoidMosaicPercentiles(selectedCollection, self.envs.percentiles[1])

        print("Process Update: Medoid calculated complete!")
        return medoid.addBands(others).addBands(medoidDown).addBands(medoidUp)

    def medoidMosaicPercentiles(self, inCollection, p):

        pBands = ee.List(self.envs.percentileBands)
        ipBands = ee.List(self.envs.inversePercentileBands)
        # function to rename bands to add percentile identifier
        def renameBands(band):
            return ee.String('p' + str(p)).cat('_').cat(ee.String(band))

        pBandNumbers = ee.List.sequence(1, pBands.length())
        ipBandNumbers = ee.List.sequence(1, ipBands.length())

        newPBand = pBands.map(renameBands)
        newIPBand = ipBands.map(renameBands)

        # calculate the mediod of percentiles
        p1 = p
        p2 = 100 - p
        med1 = self.medoidPercentiles(inCollection.select(pBands), p1).select(pBandNumbers, newPBand)
        med2 = self.medoidPercentiles(inCollection.select(ipBands), p2).select(ipBandNumbers, newIPBand)

        medoidP = ee.Image(med1).addBands(med2)
        return medoidP


    def medoidPercentiles(self, inCollection, p):

        # get bandlist
        bands = ee.Image(inCollection.first()).bandNames()

        # get the percentile raster
        percentile = inCollection.reduce(ee.Reducer.percentile([p]))
        # substract percentile from each image
        def subtractPercentile(img):
            diff = ee.Image(img).subtract(percentile).pow(ee.Image.constant(2))
            return diff.reduce('sum').addBands(img)

        percentile = inCollection.map(subtractPercentile)

        percentile = ee.ImageCollection(percentile).reduce(ee.Reducer.min(bands.length().add(1)))

        return percentile