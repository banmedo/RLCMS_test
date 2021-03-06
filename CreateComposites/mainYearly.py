from environment import environment
from importImages import importImages
from cloudBurst import cloudBurst
from brdf import brdf
from terrain2 import terrainCorrection
from compositing import createComposite
import ee

ee.Initialize()
envs = environment()

def setExportProperties(image, args):
    year = args['year']
    date =ee.Date.fromYMD(year, 01, 01)
    seasonStart = envs.seasons[args['season']][0]
    date = date.advance(seasonStart, 'day')
    return image.set("Export_Scale", envs.exportScale,
        "Max_Cloud_Cover", args['maxCloudCover'],
        "SLC", args['SLC'],
        "MAX_SATELLITE_ZENITH", envs.MAX_SATELLITE_ZENITH,
        "MAX_DISTANCE", envs.MAX_DISTANCE,
        "Terrain_Scale", envs.terrainScale,
        "system:time_start", date.millis(),
        "zScoreThreshold", envs.zScoreThresh,
        "shadowSumThreshold", envs.shadowSumThresh,
        "cloudScoreThreshold", envs.cloudScoreThresh,
        "cloudScorePctl", envs.cloudScorePctl,
        "contractPixels", envs.contractPixels,
        "dilatePixels", envs.dilatePixels,
    )

def exportHelper(image, assetID, imageCollectionID, args):
    import time
    t = time.strftime("%Y%m%d_%H%M%S")
    image = image.multiply(10000).int16()
    image = setExportProperties(image, args)

    task = ee.batch.Export.image.toAsset(
        image=ee.Image(image),
        description=args['season']+"-"+assetID +"-"+ t,
        assetId=imageCollectionID+assetID,
        region=args['region']['coordinates'],
        maxPixels=1e13,
        scale= envs.exportScale)

    task.start()

    print('Started Exporting '+assetID+t)

def getComposites(args):
    if not('maxCloudCover' in args):
        args['maxCloudCover'] = envs.defaults['maxCloudCover']
    if not('season' in args):
        args['season'] = envs.defaults['season']
    if not('SLC' in args):
        args['SLC'] = envs.defaults['SLC']
    importImg = importImages()
    imageColl = importImg.getImagesInAYear(args)
    print("Number of Images Found: ")#, imageColl.size().getInfo())
    imageColl = cloudBurst().runModel(imageColl, args['region'])
    imageColl = brdf().runModel(imageColl)
    imageColl = terrainCorrection().runModel(imageColl)
    composite = createComposite().getMedoidAndPercentiles(imageColl)
    assetID = str(args['year'])
    imageCollectionID = envs.yearlyCollFolder+args['repo']+'composites/'
    #print(composite.bandNames().getInfo())
    exportHelper(composite, assetID, imageCollectionID, args)

if (__name__ == '__main__'):
    season = 'allyear'
    year = 2015
    # nepal = ee.FeatureCollection('ft:1tdSwUL7MVpOauSgRzqVTOwdfy17KDbw-1d9omPw').filter(ee.Filter.inList('Country', ['Nepal'])).first().geometry().getInfo()
    # print(nepal)

    region = envs.afgn
    # getComposites({'year': year, 'region': nepal, 'season': season})

    for year in range(2000,2018):
        print('trying to export for '+ str(year))
        getComposites({'year': year, 'region': region, 'season': season, 'repo':'afgn_'})