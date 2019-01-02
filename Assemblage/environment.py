import ee

class environment(object):

    def __init__(self):
        ee.Initialize()
        self.PI = ee.Number(3.14159265359)
        #environment for adding covariates
        self.repository = 'projects/servir-hkh/ncomp_seasonal_30/'
        self.repositoryYearly = 'projects/servir-hkh/ncomp_yearly_30/'

        nepalBounds = ee.FeatureCollection('ft:1tdSwUL7MVpOauSgRzqVTOwdfy17KDbw-1d9omPw').filter(ee.Filter.inList('Country', ['Nepal'])).first().geometry()
        # nep2 = ee.FeatureCollection('projects/servir-hkh/RLCMSsmooth/regions').geometry()

        self.boundary = nepalBounds.buffer(20000).getInfo()
        # self.boundary = nep2.buffer(1000).getInfo()

        self.exportScale = 30

        self.primitives = ['settlement', 'forest', 'cropland', 'wetland', 'otherland', 'grassland']

        self.DTstring = '\n'.join(['1) root 9999 9999 9999',\
            '2) forest>=80 9999 9999 1 *',\
            '3) forest<80 9999 9999 9999',\
            '6) settlement>=70 9999 9999 2 *',\
            '7) settlement<70 9999 9999 9999',\
            '14) wetland>=70 9999 9999 3 *',\
            '15) wetland<70 9999 9999 9999',\
            '30) grassland>=60 9999 9999 4 *',\
            '31) grassland<60 9999 9999 9999',\
            '62) cropland>=60 9999 9999 5 *',\
            '63) cropland<60 9999 9999 0 *'])