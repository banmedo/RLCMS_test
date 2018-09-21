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
# published functions are 'whittakerSmoothing'
#
# --------------------------------------------------------------------
# Managing Imports
from utils import *
import ee
ee.Initialize()

# Function to compute the inverse log ratio of a regression results to
# transform back to percent units
def inverseLogRatio(image):
  bands = image.bandNames()
  ilrImage = ee.Image(100).divide(ee.Image(1).add(image.exp())).rename(bands)
  return ilrImage

def whittakerSmoothing(imageCollection, isCompositional = False, lamb = 5):
    # quick configs to set defaults
    def toFl(image):
        return image.toFloat()

    # procedure start
    ic = imageCollection.map(toFl)

    dimension = ic.size()
    identity_mat = ee.Array.identity(dimension)
    difference_mat = getDifferenceMatrix(identity_mat,3)
    difference_mat_transpose = difference_mat.transpose()
    lamda_difference_mat = difference_mat_transpose.multiply(lamb)
    res_mat = lamda_difference_mat.matrixMultiply(difference_mat)
    hat_matrix = res_mat.add(identity_mat)

    # backing up original data
    original = ic

    def getProperties(image):
        return ee.Image(image).toDictionary()

    # get original image properties
    properties = ic.toList(10000).map(getProperties)


    # if data is compositional
    # calculate the logratio of an image between 0 and 100. First
    # clamps between delta and 100-delta, where delta is a small positive value.
    if (isCompositional):

        def clampImage(image):
            delta = 0.001
            bands = image.bandNames()
            image = image.clamp(delta,100-delta)
            image = (ee.Image.constant(100).subtract(image)).divide(image).log().rename(bands)
            return image

        ic = ic.map(clampImage)

    arrayImage = original.toArray()
    coeffimage = ee.Image(hat_matrix).updateMask(arrayImage.mask())
    smoothImage = coeffimage.matrixSolve(arrayImage)

    def getImageId(image):
        return ee.Image(image).id()

    idlist = ic.toList(10000).map(getImageId)

    bandlist = ee.Image(ic.first()).bandNames()

    flatImage = smoothImage.arrayFlatten([idlist,bandlist])
    smoothCollection = ee.ImageCollection(unpack(flatImage, idlist, bandlist))

    if (isCompositional):
        smoothCollection = smoothCollection.map(inverseLogRatio)

    def addSuffix(band):
        return ee.String(band).cat('_fitted')

    # get new band names by adding suffix fitted
    newBandNames = bandlist.map(addSuffix)

    # rename the bands in smoothened images
    smoothCollection = smoothCollection.select(bandlist, newBandNames)

    # a really dumb way to loose the google earth engine generated ID so that the two
    # images can be combined for the chart
    dumbimg = arrayImage.arrayFlatten([idlist,bandlist])
    dumbcoll = ee.ImageCollection(unpack(dumbimg,idlist, bandlist))
    outCollection = dumbcoll.combine(smoothCollection)

    outCollList = outCollection.toList(10000)
    def addPropBack(image):
        return ee.Image(image).set(properties.get(outCollList.indexOf(image)))

    outCollectionProp = outCollList.map(addPropBack)

    residue_sq = smoothImage.subtract(arrayImage).pow(ee.Image(2)).divide(dimension)
    rmse_array = residue_sq.arrayReduce(ee.Reducer.sum(),[0]).pow(ee.Image(1/2))

    rmseImage = rmse_array.arrayFlatten([["rmse"],bandlist])

    return (ee.ImageCollection(outCollectionProp), rmseImage)
    # return ee.ImageCollection.fromImages(outCollectionProp)

# --------------------------------------------------------------------
# Author: Nishanta Khanal
# Organization: ICIMOD
# Contact: nkhanal@icimod.org
# --------------------------------------------------------------------
