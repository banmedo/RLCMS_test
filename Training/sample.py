import ee
from environment import environment

class sample(object):

    def __init__(self):
        ee.Initialize()
        self.envs = environment()

    def sampleData(self, image, trainingPoints, inputLandClass, primitive, boundary):
        image = image.clip(boundary)

        def remapClassValues(feature):
            return feature.set('land_class', 1)

        def remapOtherValues(feature):
            return feature.set('land_class', 0)

        wa = trainingPoints.filter(ee.Filter.eq(inputLandClass, primitive)).map(remapClassValues)
        ot = trainingPoints.filter(ee.Filter.neq(inputLandClass, primitive))
        ot = ot.randomColumn('random').limit(wa.size(), 'random')
        ot = ot.map(remapOtherValues)

        mergedPoints = wa.merge(ot)

        sampledPoints = image.sampleRegions(collection= mergedPoints,scale=self.envs.sampleScale,properties=['land_class'])
        return sampledPoints
