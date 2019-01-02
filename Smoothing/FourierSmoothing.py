# library to apply whittaker smoothing to a image collection having images with
# continous data
#
# function takes image collection [type ee.ImageCollection],
# whether data is compositional [type boolean] (optional, default false)
# and lambda [type integer] (optional, default 5)
# images in collection must have property 'system:time_start'
#
# returns a corresponding image collection with temporally smoothened images
# and a rmse images which has pixelwise rmse for each band
#
# published functions are 'fourierTransformImage', 'fourierTransformArray'
# 'fourierSmoothing
#
# --------------------------------------------------------------------
# Managing Imports
from utils import *
import ee
ee.Initialize()

def fourierTransformImage(size, realArrayImg, imgArrayImg=False, isInverse=False):
  N = size
  n = ee.Array([ee.List.sequence(0,ee.Number(N).subtract(1))])
  k = n.transpose()
  pi = 3.141592653589793
  factor = -2
  if (isInverse):
    factor = 2
  theta = k.multiply(factor*pi).divide(N).matrixMultiply(n)
  cos_theta = ee.Image(theta.cos())
  sin_theta = ee.Image(theta.sin())
  if (isInverse):
    cos_theta = cos_theta.divide(N)
    sin_theta = sin_theta.divide(N)

  cos_theta = cos_theta.updateMask(realArrayImg.mask())
  sin_theta = sin_theta.updateMask(realArrayImg.mask())
  r_cos_theta = realArrayImg.matrixMultiply(cos_theta)
  r_sin_theta = realArrayImg.matrixMultiply(sin_theta)
  realComponent = r_cos_theta
  imaginaryComponent = r_sin_theta
  if (imgArrayImg):
    i_sin_theta = imgArrayImg.matrixMultiply(sin_theta)
    i_cos_theta = imgArrayImg.matrixMultiply(cos_theta)
    realComponent = realComponent.subtract(i_sin_theta)
    imaginaryComponent = imaginaryComponent.add(i_cos_theta)

  return {'real':realComponent, 'imaginary':imaginaryComponent}

def fourierTransformArray(size, realArray, imgArray, isInverse):
  N = size
  n = ee.Array([ee.List.sequence(0,N-1)])
  k = n.transpose()
  pi = 3.141592653589793
  factor = -2
  if (isInverse):
    factor = 2
  theta = k.multiply(factor*pi).divide(N).matrixMultiply(n)
  cos_theta = theta.cos()
  sin_theta = theta.sin()
  if (isInverse):
    cos_theta = cos_theta.divide(N)
    sin_theta = sin_theta.divide(N)

  r_cos_theta = realArray.matrixMultiply(cos_theta)
  r_sin_theta = realArray.matrixMultiply(sin_theta)
  realComponent = r_cos_theta
  imaginaryComponent = r_sin_theta
  if (imgArray):
    i_sin_theta = imgArray.matrixMultiply(sin_theta)
    i_cos_theta = imgArray.matrixMultiply(cos_theta)
    realComponent = realComponent.subtract(i_sin_theta)
    imaginaryComponent = imaginaryComponent.add(i_cos_theta)

  return {'real':realComponent, 'imaginary':imaginaryComponent}

def fourierSmoothing(imageCollection, smoothingDegree):
  notice = "Note: In order to avoid errors make sure the masks"+\
              "in each image in the collection is same. It is better to have"+\
              "unmasked images so unmask the images with proper values if possible."
  print(notice)
  ic = imageCollection
  sd = smoothingDegree or 10
  arraySize = ic.size()

  def getImageId(image):
    return ee.Image(image).id()

  imgIds = ic.toList(arraySize).map(getImageId)

  def getProperties(image):
    return ee.Image(image).toDictionary()
  # get original image properties
  properties = ic.toList(arraySize).map(getProperties)

  bandList = ee.Image(ic.first()).bandNames()
  slicesize = arraySize.divide(2).add(1).floor().int()

  # collectionMask = ee.Image(ic.first()).mask()

  def unmaskImg(image):
      return image.unmask(0,False)

  ic = ic.map(unmaskImg)

  arrayImage = ic.toArray().arrayTranspose()
  fourierTransformed = fourierTransformImage(ic.size(),arrayImage)
  r_zeroAppend = fourierTransformed['real']
  i_zeroAppend = fourierTransformed['imaginary']
  if(arraySize.gt(sd).getInfo()):
    r_sliced = fourierTransformed['real'].arraySlice(1,0,sd)
    i_sliced = fourierTransformed['imaginary'].arraySlice(1,0,sd)

    zeroArray = ee.List.repeat(ee.List.repeat(0,ic.size()),bandList.size())
    zeroTail = ee.Array(zeroArray).slice(1,sd)
    r_zeroAppend = r_sliced.arrayCat(zeroTail,1)
    i_zeroAppend = i_sliced.arrayCat(zeroTail,1)

  smoothened = fourierTransformImage(arraySize, r_zeroAppend, i_zeroAppend, True)
  smoothImage = ee.Image(smoothened['real'].arrayTranspose())

  flattenedImage = smoothImage.arrayFlatten([imgIds, bandList])
  smoothCollection = unpack(flattenedImage, imgIds, bandList)
  originalCollection = unpack(arrayImage.arrayTranspose().arrayFlatten([imgIds, bandList]), imgIds, bandList)
  # get new band names by adding suffix fitted
  def renameBands(band):
    return ee.String(band).cat("_fitted")
  newBandNames = bandList.map(renameBands)
  # rename the bands in smoothened images
  def renameBandsAndUpdateMask(image):
    return ee.Image(image).rename(newBandNames)

  smoothCollection = smoothCollection.map(renameBandsAndUpdateMask)
  finalCollection = originalCollection.combine(smoothCollection)

  def reassignProperties(image,list):
    return ee.List(list).add(image.set(properties.get(ee.List(list).size())))

  finalCollection = finalCollection.iterate(reassignProperties,[])

  residue_sq = smoothImage.subtract(arrayImage.arrayTranspose()).pow(ee.Image(2)).divide(arraySize)
  rmse_array = residue_sq.arrayReduce(ee.Reducer.sum(),[0]).pow(ee.Image(1/2))

  rmseImage = rmse_array.arrayFlatten([["rmse"],bandList])

  return [ee.ImageCollection.fromImages(finalCollection), rmseImage]


# --------------------------------------------------------------------
# Author: Nishanta Khanal
# Organization: ICIMOD
# Contact: nkhanal@icimod.org
# --------------------------------------------------------------------
