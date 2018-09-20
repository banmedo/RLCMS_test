from environment import environment
from addCovariates import addCovariates
from sample import sample
import ee

class trainData(object):
    def __init__(self, year, primitive):
        ee.Initialize()
        self.envs = environment()
        self.year = year
        self.primitive = primitive

    def getCovariateImage(self, year):
        return addCovariates().runModel(self.envs.repository, year)

    def samplePoints(self, covImage, year, primitive):
        #filter out features for year
        tps = self.envs.trainingPoints.filter(ee.Filter.inList(self.envs.yearField,[year]))
        #sample data over training points
        sampledPoints = sample().sampleData(covImage, tps, self.envs.inputLandClass, primitive, self.envs.boundary)
        return sampledPoints


    def classifyImage(self, covImage, sampledPoints):
        boundary = self.envs.boundary
        bandNames = covImage.bandNames().remove('land_class')
        classifier = ee.Classifier.randomForest(self.envs.numberOfTrees) \
        .setOutputMode('PROBABILITY') \
        .train(features = sampledPoints,classProperty = 'land_class',inputProperties =  bandNames)

        classifiedImage = covImage.clip(boundary).classify(classifier)

        # confusionMatrix = classifier.confusionMatrix()

        return classifiedImage

    def exportImage(self, image, year, primitive):
        year = str(year)
        task =  ee.batch.Export.image.toAsset(
            image =  image,
            description= 'Export-' + primitive + '-' + year,
            assetId= self.envs.repository + 'primi/' + primitive + '-' + year +'_300m',
            region= self.envs.boundary['coordinates'],
            scale= self.envs.exportScale,
            maxPixels = 1e13
        )

        task.start()
        print("Started exporting ", self.envs.repository + 'primi/' + primitive + '-' + year +'_300m')

    def runModel(self):
        covImage = self.getCovariateImage(self.year)
        sampledPoints = self.samplePoints(covImage, self.year, self.primitive)
        # print(sampledPoints.size().getInfo())
        classifiedImage = self.classifyImage(covImage, sampledPoints)
        self.exportImage(classifiedImage, self.year, self.primitive)

if (__name__ == '__main__'):
    year = 2013
    primitive = 'cropland'
    # trainData(year, primitive).runModel()
    for year in range (2010, 2013):
        trainData(year, 'cropland').runModel()
        trainData(year, 'wetland').runModel()
        trainData(year, 'forest').runModel()
        trainData(year, 'settlement').runModel()
        trainData(year, 'otherland').runModel()
        trainData(year, 'grassland').runModel()