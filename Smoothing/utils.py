import ee
ee.Initialize()

# unpacks an array image into images and bands
# takes an array image, list of image IDs and list
# of band names as arguments
def unpack(arrayImage, imageIds, bands):
    def iter(item, icoll):
        def innerIter(innerItem, innerList):
            return ee.List(innerList).add(ee.String(item).cat("_").cat(ee.String(innerItem)))
        temp = bands.iterate(innerIter, ee.List([]))

        return ee.ImageCollection(icoll)\
            .merge(ee.ImageCollection(ee.Image(arrayImage).select(temp,bands).set("id",item)))

    imgcoll  = ee.ImageCollection(imageIds.iterate(iter, ee.ImageCollection([])))
    return imgcoll

# function to get a Difference mattrix of specified order
# on the input matrix. takes matrix and order as parameters
def getDifferenceMatrix(inputMatrix, order):
    rowCount = ee.Number(inputMatrix.length().get([0]))
    left = inputMatrix.slice(0,0,rowCount.subtract(1))
    right = inputMatrix.slice(0,1,rowCount)
    if (order > 1 ):
        return getDifferenceMatrix(left.subtract(right), order-1)
    return left.subtract(right)

# --------------------------------------------------------------------
# Author: Nishanta Khanal
# Organization: ICIMOD
# Contact: nkhanal@icimod.org
# --------------------------------------------------------------------
