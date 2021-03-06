import ee

class environment(object):

    def __init__(self):
        ee.Initialize()
        self.PI = ee.Number(3.14159265359)
        #environment for adding covariates
        self.repository = 'projects/servir-hkh/ncomp_seasonal_30/'
        self.repositoryYearly = 'projects/servir-hkh/ncomp_yearly_30/'

        self.isolatedDatasets = [
            ['elevation', 'USGS/SRTMGL1_003', 0],
            #['jrc', 'JRC/GSW1_0/GlobalSurfaceWater',2,['occurrence', 'change_abs', 'change_norm', 'seasonality', 'transition', 'max_extent']]
        ]

        self.covseasons = [
            'drycool',
            'dryhot',
            'rainy'
        ]

        self.covariates = [
            ['blue', 'green'],
            ['blue', 'red'],
            ['blue', 'nir'],
            ['blue', 'swir1'],
            ['blue', 'swir2'],
            ['green', 'red'],
            ['green', 'nir'],
            ['green', 'swir1'],
            ['green', 'swir2'],
            ['red', 'swir1'],
            ['red', 'swir2'],
            ['nir', 'red'],
            ['nir', 'swir1'],
            ['nir', 'swir2'],
            ['swir1', 'swir2']
        ]

        self.ratios = [
            ['swir1', 'nir'],
            ['red', 'swir1']
        ]

        self.expressions = [
            ['evi', '2.5 * ((img.nir - img.red) / (img.nir + 6 * img.red - 7.5 * img.blue + 1))'],
            ['savi', '1.5 * (img.nir - img.red) / (img.nir+img.red+0.5)']
        ]

        nepalBounds = ee.FeatureCollection('ft:1tdSwUL7MVpOauSgRzqVTOwdfy17KDbw-1d9omPw').filter(ee.Filter.inList('Country', ['Nepal'])).first().geometry()
        self.boundary = nepalBounds.buffer(20000).getInfo()

        # self.trainingPoints = ee.FeatureCollection('projects/servir-hkh/RLCMS_Nepal07302018/Training_Sample/Nepal_samples_all_validation')
        self.trainingPoints = ee.FeatureCollection("projects/servir-hkh/nk-comp/training-with-year")
        # training data contains following number of points per classes
        # cropland: 2291
        # forest: 4070
        # grassland: 974
        # otherland: 2321
        # settlement: 547
        # wetland: 115

        self.inputLandClass = 'land_use_c'
        self.yearField = 'rs_date_ye'

        self.sampleScale = 30

        self.exportScale = 30

        self.numberOfTrees = 500
