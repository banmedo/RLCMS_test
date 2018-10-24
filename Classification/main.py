from environment import environment
import sys
sys.path.append('../Training')
from addCovariates import addCovariates
import ee

class trainData(object):
    def __init__(self, year, primitive):
        ee.Initialize()
        self.envs = environment()
        self.year = year
        self.primitive = primitive

    def getCovariateImage(self, year):
        return addCovariates().runModel(self.envs.repository, year)

    def reclassSampledPoints(self, trainingPoints, inputLandClass, primitive):
        def remapClassValues(feature):
            return feature.set('land_class', 1)

        def remapOtherValues(feature):
            return feature.set('land_class', 0)

        wa = trainingPoints.filter(ee.Filter.eq(inputLandClass, primitive)).map(remapClassValues)
        ot = trainingPoints.filter(ee.Filter.neq(inputLandClass, primitive))
        ot = ot.randomColumn('random').limit(wa.size(), 'random')
        ot = ot.map(remapOtherValues)

        mergedPoints = wa.merge(ot)

        return mergedPoints


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
            assetId= self.envs.repository + 'primi/' + primitive + '-' + year,
            region= self.envs.boundary['coordinates'],
            scale= self.envs.exportScale,
            maxPixels = 1e13
        )

        task.start()
        print("Started exporting ", self.envs.repository + 'primi/' + primitive + '-' + year)

    def runModel(self):
        covImage = self.getCovariateImage(self.year)
        trainingPoints = self.reclassSampledPoints(self.envs.sampledPoints, \
                                                   self.envs.inputLandClass, \
                                                   self.primitive)
        # print(sampledPoints.size().getInfo())
        classifiedImage = self.classifyImage(covImage, trainingPoints)
        self.exportImage(classifiedImage, self.year, self.primitive)

if (__name__ == '__main__'):
    # year = 2013
    # primitive = 'cropland'
    # trainData(year, primitive).runModel()
    for year in range (2000, 2018):
        trainData(year, 'cropland').runModel()
        trainData(year, 'wetland').runModel()
        trainData(year, 'forest').runModel()
        trainData(year, 'settlement').runModel()
        trainData(year, 'otherland').runModel()
        trainData(year, 'grassland').runModel()