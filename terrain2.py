import ee
from environment import environment

class terrainCorrection(object):

    def __init__(self):
        ee.Initialize()
        self.envs = environment()

    def topoCorr_IC(self, img):
        dem = ee.Image(self.envs.dem30m)
        # Extract image metadata about solar position
        SZ_rad = ee.Image.constant(ee.Number(img.get('SOLAR_ZENITH_ANGLE'))).multiply(3.14159265359).divide(180).clip(
            img.geometry().buffer(10000))
        SA_rad = ee.Image.constant(ee.Number(img.get('SOLAR_AZIMUTH_ANGLE')).multiply(3.14159265359).divide(180)).clip(
            img.geometry().buffer(10000))
        # Creat terrain layers
        slp = ee.Terrain.slope(dem).clip(img.geometry().buffer(10000))
        slp_rad = ee.Terrain.slope(dem).multiply(3.14159265359).divide(180).clip(img.geometry().buffer(10000))
        asp_rad = ee.Terrain.aspect(dem).multiply(3.14159265359).divide(180).clip(img.geometry().buffer(10000))

        # Calculate the illumination condition
        # slope part of the illumination condition
        cosZ = SZ_rad.cos()
        cosS = slp_rad.cos()
        slope_illumination = cosS.expression("cosZ * cosS",
                                             {'cosZ': cosZ,
                                              'cosS': cosS.select(['slope'])})
        # aspect part of the illumination condition
        sinZ = SZ_rad.sin()
        sinS = slp_rad.sin()
        cosAziDiff = (SA_rad.subtract(asp_rad)).cos()
        aspect_illumination = sinZ.expression("sinZ * sinS * cosAziDiff",
                                              {'sinZ': sinZ,
                                               'sinS': sinS,
                                               'cosAziDiff': cosAziDiff})
        # full illumination condition
        ic = slope_illumination.add(aspect_illumination)

        # Add IC to original image
        img_plus_ic = ee.Image(
            img.addBands(ic.rename(['IC'])).addBands(cosZ.rename(['cosZ'])).addBands(cosS.rename(['cosS'])).addBands(
                slp.rename(['slope'])))
        return img_plus_ic

    def topoCorr_SCSc(self, img):
        img_plus_ic = img
        mask1 = img_plus_ic.select(['nir']).gt(-0.1)
        mask2 = img_plus_ic.select(['slope']).gte(5)\
                    .And (img_plus_ic.select(['IC']).gte(0))\
                    .And (img_plus_ic.select(['nir']).gt(-0.1))
        img_plus_ic_mask2 = ee.Image(img_plus_ic.updateMask(mask2))

        # Specify bands to topographically correct
        bandList = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']

        scale = self.envs.terrainScale

        geom = img.geometry().buffer(-5000)
        def apply_SCSccorr(band):
            method = 'SCSc'
            out = img_plus_ic_mask2.select(['IC', band]).reduceRegion(
                reducer =  ee.Reducer.linearFit(),  # Compute coefficients: a(slope), b(offset), c(b / a)
                # trim off the outer edges of the image for linear relationship
                geometry = geom ,
                scale = scale,
                maxPixels = 1e10
            )

            out_a = ee.Number(out.get('scale'))
            out_b = ee.Number(out.get('offset'))
            out_c = ee.Number(out.get('offset')).divide(ee.Number(out.get('scale')))

            # apply the SCSc correction
            SCSc_output = img_plus_ic_mask2.expression("((image * (cosB * cosZ + cvalue)) / (ic + cvalue))", {
                'image': img_plus_ic_mask2.select([band]),
                'ic': img_plus_ic_mask2.select(['IC']),
                'cosB': img_plus_ic_mask2.select(['cosS']),
                'cosZ': img_plus_ic_mask2.select(['cosZ']),
                'cvalue': out_c
            })

            return ee.Image(SCSc_output).set(band+'_scale', out_a, band+'_offset', out_b, band+'_offset_scale_ratio', out_c)

        img_SCSccorr = ee.Image([apply_SCSccorr(band) for band in bandList]).addBands(img_plus_ic.select('IC'));
        return img_SCSccorr

        bandList_IC = ee.List([bandList, 'IC']).flatten()
        return img_SCSccorr.unmask(img_plus_ic.select(bandList_IC))\
            .addBands(mask1.rename(['initMask']))\
            .addBands(mask2.rename(['corrMask']))

    def runModel(self, imageCollection):
        ic = imageCollection.map(self.topoCorr_IC)
        ic = ic.map(self.topoCorr_SCSc)
        print("Process Update: Terrain Correction complete!", ic.size().getInfo())
        return ic