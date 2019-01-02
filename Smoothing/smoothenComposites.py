import sys
sys.path.append('../Training')
from addCovariates import addCovariates

import ee
ee.Initialize()
from LinearFit import linearFitSmoothing

# specify the study region
basset = ee.FeatureCollection('projects/servir-hkh/RLCMSsmooth/regions').geometry()
boundary = basset.buffer(1000)
exportgeom = [[[86.67602630230613, 28.233783180530544],
          [85.09948821636863, 27.86534047795426],
          [85.29724212261863, 26.669097326308105],
          [85.70373626324363, 26.796653769859198],
          [87.02209563824363, 27.446903199454304],
          [87.09899993511863, 27.826483727611077],
          [86.87927337261863, 28.156321292339296]]]

# specify repository
repository = 'projects/servir-hkh/ncomp_yearly_30/'
imageCollection = ee.ImageCollection(repository+'composites')

#####################################3
# perform smoothing
#####################################3
#add image attribures for smoothing
def prepareImage(image):
    imgYear = ee.Number.parse(image.id())
    # image = image.unmask(0).clip(boundary).toShort()
    image = image.clip(boundary).toShort()
    return image.set('year', imgYear, 'system:time_start', ee.Date.fromYMD(imgYear, 1, 1).millis());

imageCollection = imageCollection.map(prepareImage)

# get original band names and add fitted at end to select fitted bands
bandNames = ee.Image(imageCollection.first()).bandNames()
def fittedName(band):
    return ee.String(band).cat('_fitted')
fittedNames = bandNames.map(fittedName)

smoothingResults = linearFitSmoothing(imageCollection, 367)
imageCollection = smoothingResults[0].select(fittedNames, bandNames)
rmse = smoothingResults[1]

def exportHelper(image, assetID, imageCollectionID):
    import time
    t = time.strftime("%Y%m%d_%H%M%S")
    image = image.int16()
    # image = setExportProperties(image, args)
    task = ee.batch.Export.image.toAsset(
        image=ee.Image(image),
        description="linearFit-"+assetID +"-"+ t,
        assetId=imageCollectionID+assetID,
        region=exportgeom,
        maxPixels=1e13,
        scale= 30)

    task.start()

    print('Started Exporting '+assetID+t)

# year = 2000
# image = ee.Image(imageCollection.filter(ee.Filter.eq('year',year)).first()).clip(boundary)
# exportHelper(image, str(year),'projects/servir-hkh/RLCMSsmooth/linearFit/')
for year in range(2001,2018):
    image = ee.Image(imageCollection.filter(ee.Filter.eq('year',year)).first()).clip(boundary)
    exportHelper(image, str(year),'projects/servir-hkh/RLCMSsmooth/linearFit/')