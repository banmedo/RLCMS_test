import ee
from environment import environment

class createComposite(object):

    def __init__(self):
        ee.Initialize()
        self.envs = environment()

    def getMedoidAndStdevs(self, collection):
        medoidIncludeBands = self.envs.medoidIncludeBands
        stdevIncludeBands = self.envs.stdevIncludeBands
        # Find band names in first image
        f = ee.Image(collection.first())
        bandNames = f.bandNames()

        # Find the median
        median = collection.select(medoidIncludeBands).median()

        medBandList = median.bandNames()

        medBandNumbers = ee.List.sequence(1, medBandList.length())

        otherBands = bandNames.removeAll(medoidIncludeBands)

        others = collection.select(otherBands).mean()

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