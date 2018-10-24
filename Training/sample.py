import ee
from addCovariates import addCovariates
from environment import environment

class sample(object):

    def __init__(self):
        ee.Initialize()
        self.envs = environment()

    def sampledYearlyData(self, trainingPoints, year):
        trainingPoints = trainingPoints.filter(ee.Filter.eq(self.envs.yearField, year))
        covImage = addCovariates().runModelYearly(self.envs.repositoryYearly, year).clip(self.envs.boundary)
        sampledPoints = covImage.sampleRegions(
            collection = trainingPoints,\
            scale= self.envs.sampleScale,\
            properties= [self.envs.inputLandClass],\
        )
        return sampledPoints

    def runYearlyModel(self):
        trainingPoints = self.envs.trainingPoints.filterBounds(self.envs.boundary)
        sampledYears = ee.FeatureCollection([])
        for year in range(2000, 2018):
            sampledYears = sampledYears.merge(self.sampledYearlyData(trainingPoints, year))

        return sampledYears

    def exportSampledData(self, sampledData):
        task = ee.batch.Export.table.toDrive(
            collection=sampledData,\
            description='Sampled-training-points-overall',\
            folder='eeexports',\
            fileNamePrefix='yearly-training-data-overall'\
        )

        task.start()
        print('Started Exporting: yearly-training-data-overall')

if __name__ == '__main__':
    sampledData = sample().runYearlyModel()
    print(sampledData.size().getInfo())
    sample().exportSampledData(sampledData)