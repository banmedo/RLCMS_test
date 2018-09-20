import ee
from addCovariates import addCovariates

ee.Initialize()


# setup parameters
exportScale = 300

repository = 'projects/servir-hkh/nk-comp/'
year = 2012

primitive = 'grassland'
inputLandClass = 'land_use_c'
numberOfTrees = 50

nepalBounds = ee.FeatureCollection('ft:1tdSwUL7MVpOauSgRzqVTOwdfy17KDbw-1d9omPw').filter(ee.Filter.inList('Country', ['Nepal'])).first().geometry()
boundary = nepalBounds.buffer(10000).getInfo()

# fusion tables for sampled data
    # sampledTables = {
                           #   'forest-2015_300m':'1Mjq2TPnz3D20zfJ6g-1kkB0lGd_0POTbkAp9zZWL',
#   'cropland-2015_300m':'1O1TknoNpoXYSgbtXXgojpG8OcVr3lTpv29RJmgLX',
#   'wetland-2015_300m':'1ZN2NWmGXvFFkDFfYX9DXe8vBiJiz3FECgKvTf9c8',
#   'grassland-2015_300m':'1sLgO-1OtZZMefCILGZ2-0HUVTOC8zKY8P7rNVaIu',
#   'otherland-2015_300m':'1NkZ4zfADhtD5Cs-pwi4O-oLnMb7Ohv3sEPPGougN',
#   'settlement-2015_300m':'1ZSqoqT88N2eQHtlS6unC7vKMYeh_FdzUs0BFhXVM'
                            # }
# sampledPoints = ee.FeatureCollection('ft: ' +sampledTables[primitiv e +'- ' +year])

sampledTable = ee.FeatureCollection('ft:19bCYESQ-6vx3_ZOaLkycfIoSqjYcwJPXIz8LXyOw')

def classifyImage(covImage, sampledPoints, boundary):
    bandNames = covImage.bandNames().remove(inputLandClass)
    classifier = ee.Classifier.randomForest(numberOfTrees)\
        .setOutputMode('PROBABILITY')\
        .train(
            features = sampledPoints,
            classProperty = inputLandClass,
            inputProperties = bandNames
        )

    classifiedImage = covImage.clip(boundary).classify(classifier)

    return classifiedImage

def exportHelper(image, primitive, year):
    task = ee.batch.Export.image.toAsset(
        image = image,
        description = 'Export-' +primitive +'-' +year,
        assetId = repository +'primi/' +primitive +'-' +year,
        region = boundary['coordinates'],
        scale = exportScale
    )
    task.start()
    print('Started Export '+repository +'primi/' +primitive +'-' +year)

def remapClass(feature):
    return feature.set(inputLandClass, 1)

def remapOther(feature):
    return feature.set(inputLandClass, 0)

for year in range(2010, 2018):
    for primitive in ['forest','settlement','grassland','wetland','otherland','cropland']:
        year = str(year)
        #filter the sampled points for primitives
        classPoints = sampledTable.filter(ee.Filter.eq(inputLandClass ,primitive)).map(remapClass)
        otherPoints = sampledTable.filter(ee.Filter.neq(inputLandClass ,primitive))
        otherPoints = otherPoints.randomColumn('random').limit(classPoints.size() ,'random')
        otherPoints = otherPoints.map(remapOther)

        sampledPoints = classPoints.merge(otherPoints)

        covImage = addCovariates().runModel(repository, year)
        classifiedImage = classifyImage(covImage, sampledPoints, boundary)

        exportHelper(classifiedImage, primitive, year)

# -----------------------------------------------------------------
# main function takes images with covariates and sampled points
# returns an array with classified image and confusion matrix



