from environment import environment
import ee

class assemble(object):
    def __init__(self, year):
        ee.Initialize()
        self.envs = environment()
        self.year = str(year)

    def exportHelper(self, image):
        image = image.toUint8()
        task = ee.batch.Export.image.toAsset(
            image=image,
            description='Export-landCover-' + self.year,
            assetId=self.envs.repositoryYearly + 'landCover/' + self.year,
            region=self.envs.boundary['coordinates'],
            scale=self.envs.exportScale,
            maxPixels=1e13
        )

        task.start()
        print("Started exporting ", self.envs.repositoryYearly + 'landCover/' + self.year)

    def runModel(self):
        boundary = self.envs.boundary
        repository = self.envs.repository + 'primitives/'

        def getPrimitiveImages(primitive):
            return ee.Image(self.envs.repositoryYearly + 'primitives/'+ primitive + '-' + self.year).multiply(0.01).rename(primitive)

        stackImage = ee.Image(map(getPrimitiveImages,self.envs.primitives)).clip(boundary)
        classifier = ee.Classifier.decisionTree(self.envs.DTstring)
        landClass = stackImage.classify(classifier)

        self.exportHelper(landClass)

if (__name__ == '__main__'):
    # year = 2017
    # assemble(year).runModel()
    for year in range (2000, 2018):
        assemble(year).runModel()

