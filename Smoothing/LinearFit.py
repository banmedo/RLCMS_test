# library to apply smoothing to a image collection having images with
# continous data by breaking it into subsets, fitting them into a linear
# model and then taking average of the fit
#
# function takes image collection [type ee.ImageCollection],
# and the date range that the image is to be smoothened over.
# the date range is of buffer and is so applied on both ends. i.e. if the
# date range is specified as 15 days, the fit looks for data from before 15 days
# and after 15 days from the point of reference. The value for this can be infered
# from whether a substantial transition within said period is logical
#
# images in collection must have property 'system:time_start', and can have
# multiple bands
#
# returns a corresponding image collection with temporally smoothened images
# and a rmse images which has pixelwise rmse for each band
#
# published functions are 'linearFitSmoothing'
#
# --------------------------------------------------------------------
# Managing Imports
import ee
ee.Initialize()

def addTimeBand(image):
  date = ee.Date(image.get('system:time_start'))
  normDate = date.millis().divide(1e12)
  dateImg = ee.Image(normDate).toFloat().rename('time')
  return image.addBands(dateImg)

def linearFitSmoothBand(imageCollection, band, dateBuffer):
  ic = imageCollection
  band = ee.String(band)
  bandNames = ee.Image(ic.first()).bandNames()
  dateList = ee.List(ic.aggregate_array('system:time_start'))

  # print(dateList)
  def getFittedImages(date):
    d = ee.Date(date)
    start = d.advance(-1*dateBuffer, 'day')
    end = d.advance(dateBuffer, 'day')
    subColl = ic.filterDate(start, end).map(addTimeBand)

    fit = subColl.select(['time',band]).reduce(ee.Reducer.linearFit())

    def calcPredictions(img):
        return img.select('time').multiply(fit.select('scale')).add(fit.select('offset'))\
                 .rename([band]).copyProperties(img,img.propertyNames())
    # return fit
    out = subColl.map(calcPredictions)

    outList = out.toList(out.size())
    retObj = ee.Algorithms.If(subColl.size().eq(1),\
      subColl.select([band]).toList(1),\
      outList)
    return retObj

  dateColl = dateList.map(getFittedImages)
  fittedColl = ee.ImageCollection.fromImages(dateColl.flatten())

  def getMeanFit(date):
    d = ee.Date(date)
    start = d.advance(-1*dateBuffer, 'day')
    end = d.advance(dateBuffer, 'day')
    # subColl = fittedColl.filter(ee.Filter.eq('system:time_start',date))
    subColl = fittedColl.filterDate(start, end)
    original = ic.filter(ee.Filter.eq('system:time_start',date)).first()
    meanImg = subColl.mean().set('system:time_start',date).rename([band.cat('_fitted')])
    return meanImg.addBands(original).copyProperties(original, original.propertyNames())

  dateColl = dateList.map(getMeanFit)

  finalColl = ee.ImageCollection(dateColl)

  return finalColl


def linearFitSmoothing(imageCollection, dateBuffer):
  bandList = ee.Image(imageCollection.first()).bandNames()
  def renameBands(band):
      return ee.String(band).cat('_fitted')
  fitList = bandList.map(renameBands)

  def getSmoothBand(band):
      return linearFitSmoothBand(imageCollection.select([band]), band, dateBuffer)

  smoothenedCollection = bandList.map(getSmoothBand)

  def getCombinedCollection(coll, passedColl):
    passedColl = ee.ImageCollection(passedColl)
    coll = ee.ImageCollection(coll)
    retObj = ee.Algorithms.If(passedColl.size().gt(0),
      passedColl.combine(coll),
      coll
    )
    return retObj

  combinedCollection = smoothenedCollection.iterate(getCombinedCollection,ee.ImageCollection([]))
  combinedCollection = ee.ImageCollection(combinedCollection)

  smoothColl = combinedCollection.select(fitList).toArray()
  origColl = combinedCollection.select(bandList).toArray()

  residue_sq = smoothColl.subtract(origColl).pow(ee.Image(2)).divide(combinedCollection.size())
  rmse_array = residue_sq.arrayReduce(ee.Reducer.sum(),[0]).pow(ee.Image(1/2))

  rmseImage = rmse_array.arrayFlatten([["rmse"],bandList])
  return [combinedCollection, rmseImage]

# --------------------------------------------------------------------
# Author: Nishanta Khanal & Kel Markert
# Organization: ICIMOD
# Contact: nkhanal@icimod.org
# --------------------------------------------------------------------
