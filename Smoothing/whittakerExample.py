

# import the library
from WhittakerSmoothing import *

ic = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")
geometry = ee.Geometry.Point([85.330810546875, 27.712710260887476])
# selecting the required bands
imageCollection = ic.filterBounds(geometry)\
                        .filterDate('2016-01-01','2017-01-01')\
                        .select(['B1', 'B2'])

# add a property of timetamp to the image
# !!! --- requred as the "system:*" properties
# !!! --- cant be preserved while unpacking
# !!! --- smoothened image array
def setTime(image):
    return image.set('time_start', image.get('system:time_start'))

imageCollection = imageCollection.map(setTime)

# specifying if data is compositional
# i.e. whether the data has 0-100 limits for eg. percentages
dataIsCompositional = False

# apply the whittaker smoothing algorithm
smoothingResults = whittakerSmoothing(imageCollection, dataIsCompositional)
smoothenedCollection = smoothingResults[0]
rmse = smoothingResults[1]

# checking the original and smooth collection
print(imageCollection.size().getInfo(), smoothenedCollection.size().getInfo())

# --------------------------------------------------------------------
# Author: Nishanta Khanal
# Organization: ICIMOD
# Contact: nkhanal@icimod.org
# --------------------------------------------------------------------
