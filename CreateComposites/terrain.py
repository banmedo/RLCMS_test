import ee
from environment import environment

class terrainCorrection(object):

    def __init__(self):
        ee.Initiaize()

        self.envs = environment()

    def pixelArea(self, image):
        geom = ee.Geometry(image.get('system:footprint')).bounds()
        area = image.select(['red']).gt(0).reduceRegion({'reducer': ee.Reducer.sum(),\
                                                         'geometry': geom,\
                                                         'scale': 100})
        return image.set("pixelArea", area.get("red"))

    def getTopo(self, image):
        dem = ee.Image(self.envs.demID)
        dem = dem.unmask(0)
        geom = ee.Geometry(image.get('system:footprint')).bounds()
        slp_rad = ee.Terrain.slope(dem).clip(geom)
        slope = slp_rad.reduceRegion({'reducer': ee.Reducer.percentile([80]),\
                                      'geometry': geom,\
                                      'scale': 100})
        return image.set('slope', slope.get('slope'))

    def illuminationCondition(self, img):
        geom = ee.Geometry(img.get('system:footprint')).bounds().buffer(10000);

        # Definezenith and azimuth metadata
        zenithDict = {
            'TOA': 'SUN_ELEVATION',
            'SR': 'SOLAR_ZENITH_ANGLE'
        }
        azimuthDict = {
            'TOA': 'SUN_AZIMUTH',
            'SR': 'SOLAR_AZIMUTH_ANGLE'
        }
        toaOrSR = 'SR'
        # Extract solar zenith and azimuth bands
        SZ_rad = ee.Image.constant(ee.Number(img.get(zenithDict[toaOrSR]))).multiply(self.envs.degree2radian).clip(geom)
        SA_rad = ee.Image.constant(ee.Number(img.get(zenithDict[toaOrSR]))).multiply(self.envs.degree2radian).clip(geom)

        dem = ee.Image('USGS/NED')
        slp = ee.Terrain.slope(dem)
        slp_rad = ee.Terrain.slope(dem).multiply(self.envs.PI).divide(180)
        asp_rad = ee.Terrain.aspect(dem).multiply(self.envs.PI).divide(180)

        # Calculate the Illumination Condition(IC)
        # slope part of the illumination condition
        cosZ = SZ_rad.cos()
        cosS = slp_rad.cos()
        slope_illumination = cosS.expression("cosZ * cosS",
                                             {'cosZ': cosZ,
                                              'cosS': cosS.select('slope')})
        # aspect part of the illumination condition
        sinZ = SZ_rad.sin()
        sinS = slp_rad.sin()
        cosAziDiff = (SA_rad.subtract(asp_rad)).cos()
        aspect_illumination = sinZ.expression("sinZ * sinS * cosAziDiff",
                                              {'sinZ': sinZ,
                                               'sinS': sinS,
                                               'cosAziDiff': cosAziDiff})
        # full illumination condition(IC)
        ic = slope_illumination.add(aspect_illumination)

        # Add IC to original image
        return img.addBands(ic.rename('IC'))\
            .addBands(cosZ.rename('cosZ'))\
            .addBands(cosS.rename('cosS'))\
            .addBands(slp.rename('slope'))



    def illuminationCorrection(self, img):
        props = img.toDictionary()
        st = img.get('system:time_start')
        img_plus_ic = img
        mask2 = img_plus_ic.select('slope').gte(5)\
                    .And (img_plus_ic.select('IC').gte(0))\
                    .And (img_plus_ic.select('nir').gt(-0.1))
        img_plus_ic_mask2 = ee.Image(img_plus_ic.updateMask(mask2))

        # Specify Bands to topographically    correct    var
        bandList = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
        compositeBands = img.bandNames()
        nonCorrectBands = img.select(compositeBands.removeAll(bandList))

        geom = ee.Geometry(img.get('system:footprint')).bounds().buffer(10000)

        def apply_SCSccorr(band):
            method = 'SCSc'
            out = img_plus_ic_mask2.select('IC', band).reduceRegion({
                'reducer': ee.Reducer.linearFit(),
                'geometry': geom,
                'scale': self.envs.terrainScale,
                'maxPixels': 1e10
            })

            if (not out):
                return img_plus_ic_mask2.select(band)
            else:
                out_a = ee.Number(out.get('scale'))
                out_b = ee.Number(out.get('offset'))
                out_c = out_b.divide(out_a)
                # Apply the SCSc correction var
                SCSc_output = img_plus_ic_mask2.expression(
                    "((image * (cosB * cosZ + cvalue)) / (ic + cvalue))", {
                        'image': img_plus_ic_mask2.select(band),
                        'ic': img_plus_ic_mask2.select('IC'),
                        'cosB': img_plus_ic_mask2.select('cosS'),
                        'cosZ': img_plus_ic_mask2.select('cosZ'),
                        'cvalue': out_c
                    })

                return SCSc_output


        img_SCSccorr = ee.Image(bandList.map(apply_SCSccorr)) \
            .addBands(img_plus_ic.select('IC'))
        
        bandList_IC = ee.List([bandList, 'IC']).flatten()
        img_SCSccorr = img_SCSccorr.unmask(img_plus_ic.select(bandList_IC)).select(bandList);

        return img_SCSccorr.addBands(nonCorrectBands)\
            .setMulti(props)\
            .set('system:time_start', st)

    def runModel(self, collection):
        # collection = collection.map(self.pixelArea)
        # collection = collection.filter(ee.Filter.gt("pixelArea", 100))
        #
        # collection = collection.map(self.getTopo)
        #
        # correction = collection.filter(ee.Filter.gte("slope", 10))
        # notcorrection = collection.filter(ee.Filter.lt("slope", 10))
        correction = collection

        correction = correction.map(self.illuminationCondition)
        correction = correction.map(self.illuminationCorrection)

        # collection = correction.merge(notcorrection).sort("system:time_start")
        collection = correction.sort("system:time_start")

        return (collection)