from environment import environment
import ee
import math

class addCovariates(object):

    def __init__(self):
        ee.Initialize()
        self.envs = environment()

    def addIBI(self, image):
        ibia = image.expression('(2 * img.swir1)/(img.swir1 + img.nir)', {'img': image}).rename('ibia')
        ibib = image.expression('(img.nir / (img.nir + img.red)) + (img.green / (img.green + img.swir1))',
                            {'img': image}).rename('ibib')
        return image.addBands(ee.Image([ibia, ibib]).normalizedDifference(['ibia', 'ibib']).rename('ibi'))

    def addJRC(self, image):
        jrc = ee.Image('JRC/GSW1_0/GlobalSurfaceWater')\
        .select(['occurrence', 'change_abs', 'change_norm', 'seasonality', 'transition', 'max_extent'])\
        .rename(['jrc_occurrence', 'jrc_change_abs', 'jrc_change_norm', 'jrc_seasonality', 'jrc_transition', 'jrc_max_extent'])\
        .unmask(0)
        return image.addBands(jrc)

    def addTerrain(self, image):
        topo = ee.Algorithms.Terrain(image.select('elevation'))
        deg2rad = ee.Number(math.pi).divide(180)
        aspect = topo.select(['aspect'])
        aspect_rad = aspect.multiply(deg2rad)
        eastness = aspect_rad.sin().rename(['eastness']).float()
        northness = aspect_rad.cos().rename(['northness']).float()

        # Add topography bands to the image
        topo = topo.select(['slope', 'aspect']).addBands(eastness).addBands(northness)
        return image.addBands(topo)

    def addTasselCapIndices(self, img):
        """ Function to get all tasselCap indices """

        def getTasseledCap(img):
            """Function to compute the Tasseled Cap transformation and return an image"""

            coefficients = ee.Array([
                [0.3037, 0.2793, 0.4743, 0.5585, 0.5082, 0.1863],
                [-0.2848, -0.2435, -0.5436, 0.7243, 0.0840, -0.1800],
                [0.1509, 0.1973, 0.3279, 0.3406, -0.7112, -0.4572],
                [-0.8242, 0.0849, 0.4392, -0.0580, 0.2012, -0.2768],
                [-0.3280, 0.0549, 0.1075, 0.1855, -0.4357, 0.8085],
                [0.1084, -0.9022, 0.4120, 0.0573, -0.0251, 0.0238]
            ]);

            bands = ee.List(['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])

            # Make an Array Image, with a 1-D Array per pixel.
            arrayImage1D = img.select(bands).toArray()

            # Make an Array Image with a 2-D Array per pixel, 6x1.
            arrayImage2D = arrayImage1D.toArray(1)

            componentsImage = ee.Image(coefficients).matrixMultiply(arrayImage2D).arrayProject([0]).arrayFlatten(
                [['brightness', 'greenness', 'wetness', 'fourth', 'fifth', 'sixth']]).float();

            # Get a multi-band image with TC-named bands.
            return img.addBands(componentsImage);

        def addTCAngles(img):
            """ Function to add Tasseled Cap angles and distances to an image. Assumes image has bands: 'brightness', 'greenness', and 'wetness'."""

            # Select brightness, greenness, and wetness bands
            brightness = img.select('brightness');
            greenness = img.select('greenness');
            wetness = img.select('wetness');

            # Calculate Tasseled Cap angles and distances
            tcAngleBG = brightness.atan2(greenness).divide(math.pi).rename(['tcAngleBG']);
            tcAngleGW = greenness.atan2(wetness).divide(math.pi).rename(['tcAngleGW']);
            tcAngleBW = brightness.atan2(wetness).divide(math.pi).rename(['tcAngleBW']);
            tcDistBG = brightness.hypot(greenness).rename(['tcDistBG']);
            tcDistGW = greenness.hypot(wetness).rename(['tcDistGW']);
            tcDistBW = brightness.hypot(wetness).rename(['tcDistBW']);
            img = img.addBands(tcAngleBG).addBands(tcAngleGW).addBands(tcAngleBW).addBands(tcDistBG).addBands(
                tcDistGW).addBands(tcDistBW);

            return img;

        img = getTasseledCap(img)
        img = addTCAngles(img)
        return img

    def computeCovariates(self, image):
        covBands = []
        #normalized differences
        for i in range(0, len(self.envs.covariates)):
            pair = self.envs.covariates[i]
            b1 = pair[0]
            b2 = pair[1]
            covBands.append(image.normalizedDifference([b1, b2]).rename("ND_"+b1+"_"+b2))
        #ratios
        for i in range(0, len(self.envs.ratios)):
            pair = self.envs.ratios[i]
            b1 = pair[0]
            b2 = pair[1]
            covBands.append(image.select([b1]).divide(image.select([b2])).rename("R_"+b1+"_"+b2))
        # expressions
        for i in range(0, len(self.envs.expressions)):
            pair = self.envs.expressions[i]
            covBands.append(image.expression(pair[1], {'img':image}).rename(pair[0]))
        image = image.addBands(ee.Image(covBands))
        image = self.addIBI(image)
        image = self.addTasselCapIndices(image)
        return image

    def addIsolatedBands(self, image):
        isolatedBands = []
        for i in range(0,len(self.envs.isolatedDatasets)):
            entry = self.envs.isolatedDatasets[i]
            name = entry[0]
            importImage = ee.Image(entry[1])
            if (entry[2] == 0):
                isolatedBands.append(importImage.rename(name))
            else:
                bandNames =[]
                if (entry[2] == 1):
                    bandNames = importImage.bandNames()
                else:
                    bandNames = entry[3]

                def renameBands(band):
                    return ee.String(name).cat("_").cat(band)

                newNames = ee.List(bandNames).map(renameBands)
                isolatedBands.append(importImage.select(bandNames, newNames))
        image = image.addBands(isolatedBands)
        image = self.addJRC(image)
        return image

    def runModel(self, repository, year):
        seasonalBands = []

        for i in range(0,len(self.envs.covseasons)):
            season = self.envs.covseasons[i]
            image = ee.Image(repository+season+'/'+str(year))
            image = self.computeCovariates(image)

            def renameBands(band):
                return ee.String(season).cat("_").cat(band)

            bandNames = image.bandNames()
            newBandNames = bandNames.map(renameBands)

            seasonalBands.append(image.rename(newBandNames))

        withIsoBands = self.addIsolatedBands(ee.Image(seasonalBands))

        return self.addTerrain(withIsoBands)
