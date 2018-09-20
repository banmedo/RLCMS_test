import ee
from environment import environment


class brdf(object):

    def __init__(self):
        ee.Initialize()
        self.envs = environment()


    def line_from_coords(self, coordinates, fromIndex, toIndex):
        return ee.Geometry.LineString(ee.List([
            coordinates.get(fromIndex),
            coordinates.get(toIndex)]))

    def invertMask(self, mask):
        return mask.multiply(-1).add(1)

    def where(self, condition, trueValue, falseValue):
        trueMasked = trueValue.mask(condition)
        falseMasked = falseValue.mask(self.invertMask(condition))
        return trueMasked.unmask(falseMasked)

    def value(self, list, index):
        return ee.Number(list.get(index))

    def getsunAngles(self, date, footprint):
        jdp = date.getFraction('year')
        seconds_in_hour = 3600
        hourGMT = ee.Number(date.getRelative('second', 'day')).divide(seconds_in_hour)

        latRad = ee.Image.pixelLonLat().select('latitude').multiply(self.envs.PI.divide(180))
        longDeg = ee.Image.pixelLonLat().select('longitude')

        jdpr = jdp.multiply(self.envs.PI).multiply(2)

        a = ee.List([0.000075, 0.001868, 0.032077, 0.014615, 0.040849])
        meanSolarTime = longDeg.divide(15.0).add(ee.Number(hourGMT))
        localSolarDiff1 = self.value(a, 0) \
            .add(self.value(a, 1).multiply(jdpr.cos())) \
            .subtract(self.value(a, 2).multiply(jdpr.sin())) \
            .subtract(self.value(a, 3).multiply(jdpr.multiply(2).cos())) \
            .subtract(self.value(a, 4).multiply(jdpr.multiply(2).sin()))

        localSolarDiff2 = localSolarDiff1.multiply(12 * 60)

        localSolarDiff = localSolarDiff2.divide(self.envs.PI)
        trueSolarTime = meanSolarTime \
            .add(localSolarDiff.divide(60)) \
            .subtract(12.0)

        ah = trueSolarTime.multiply(ee.Number(self.envs.MAX_SATELLITE_ZENITH * 2).multiply(self.envs.PI.divide(180)))
        b = ee.List([0.006918, 0.399912, 0.070257, 0.006758, 0.000907, 0.002697, 0.001480])
        delta = self.value(b, 0) \
            .subtract(self.value(b, 1).multiply(jdpr.cos())) \
            .add(self.value(b, 2).multiply(jdpr.sin())) \
            .subtract(self.value(b, 3).multiply(jdpr.multiply(2).cos())) \
            .add(self.value(b, 4).multiply(jdpr.multiply(2).sin())) \
            .subtract(self.value(b, 5).multiply(jdpr.multiply(3).cos())) \
            .add(self.value(b, 6).multiply(jdpr.multiply(3).sin()))

        cosSunZen = latRad.sin().multiply(delta.sin()) \
            .add(latRad.cos().multiply(ah.cos()).multiply(delta.cos()))
        sunZen = cosSunZen.acos()

        sinSunAzSW = ah.sin().multiply(delta.cos()).divide(sunZen.sin())
        sinSunAzSW = sinSunAzSW.clamp(-1.0, 1.0)

        cosSunAzSW = (latRad.cos().multiply(-1).multiply(delta.sin())
                      .add(latRad.sin().multiply(delta.cos()).multiply(ah.cos()))) \
            .divide(sunZen.sin())
        sunAzSW = sinSunAzSW.asin()

        sunAzSW = self.where(cosSunAzSW.lte(0), sunAzSW.multiply(-1).add(self.envs.PI), sunAzSW)
        sunAzSW = self.where(cosSunAzSW.gt(0).And (sinSunAzSW.lte(0)), sunAzSW.add(self.envs.PI.multiply(2)), sunAzSW)

        sunAz = sunAzSW.add(self.envs.PI)
        # Keep within [0, 2pi] range
        sunAz = self.where(sunAz.gt(self.envs.PI.multiply(2)), sunAz.subtract(self.envs.PI.multiply(2)), sunAz)

        footprint_polygon = ee.Geometry.Polygon(footprint)
        sunAz = sunAz.clip(footprint_polygon)
        sunAz = sunAz.rename(['sunAz'])
        sunZen = sunZen.clip(footprint_polygon).rename(['sunZen'])

        return [sunAz, sunZen]

    def azimuth(self, footprint):
        def x(point):
            return ee.Number(ee.List(point).get(0))

        def y(point):
            return ee.Number(ee.List(point).get(1))

        upperCenter = self.line_from_coords(footprint, self.envs.UPPER_LEFT, self.envs.UPPER_RIGHT).centroid().coordinates()
        lowerCenter = self.line_from_coords(footprint, self.envs.LOWER_LEFT, self.envs.LOWER_RIGHT).centroid().coordinates()
        slope = ((y(lowerCenter)).subtract(y(upperCenter))).divide((x(lowerCenter)).subtract(x(upperCenter)))
        slopePerp = ee.Number(-1).divide(slope)
        azimuthLeft = ee.Image(self.envs.PI.divide(2).subtract((slopePerp).atan()))
        return azimuthLeft.rename(['viewAz'])

    def zenith(self, footprint):
        leftLine = self.line_from_coords(footprint, self.envs.UPPER_LEFT, self.envs.LOWER_LEFT)
        rightLine = self.line_from_coords(footprint, self.envs.UPPER_RIGHT, self.envs.LOWER_RIGHT)
        leftDistance = ee.FeatureCollection(leftLine).distance(self.envs.MAX_DISTANCE)
        rightDistance = ee.FeatureCollection(rightLine).distance(self.envs.MAX_DISTANCE)
        viewZenith = rightDistance.multiply(ee.Number(self.envs.MAX_SATELLITE_ZENITH * 2)) \
            .divide(rightDistance.add(leftDistance)) \
            .subtract(ee.Number(self.envs.MAX_SATELLITE_ZENITH)) \
            .clip(ee.Geometry.Polygon(footprint)) \
            .rename(['viewZen'])
        return viewZenith.multiply(self.envs.PI.divide(180))

    def _kvol(self, sunAz, sunZen, viewAz, viewZen):
        relative_azimuth = sunAz.subtract(viewAz).rename(['relAz'])
        pa1 = viewZen.cos().multiply(sunZen.cos())
        pa2 = viewZen.sin().multiply(sunZen.sin()).multiply(relative_azimuth.cos())
        phase_angle1 = pa1.add(pa2)
        phase_angle = phase_angle1.acos()
        p1 = ee.Image(self.envs.PI.divide(2)).subtract(phase_angle)
        p2 = p1.multiply(phase_angle1)
        p3 = p2.add(phase_angle.sin())
        p4 = sunZen.cos().add(viewZen.cos())
        p5 = ee.Image(self.envs.PI.divide(4))

        kvol = p3.divide(p4).subtract(p5).rename(['kvol'])

        viewZen0 = ee.Image(0)
        pa10 = viewZen0.cos().multiply(sunZen.cos())
        pa20 = viewZen0.sin().multiply(sunZen.sin()).multiply(relative_azimuth.cos())
        phase_angle10 = pa10.add(pa20)
        phase_angle0 = phase_angle10.acos()
        p10 = ee.Image(self.envs.PI.divide(2)).subtract(phase_angle0)
        p20 = p10.multiply(phase_angle10)
        p30 = p20.add(phase_angle0.sin())
        p40 = sunZen.cos().add(viewZen0.cos())
        p50 = ee.Image(self.envs.PI.divide(4))

        kvol0 = p30.divide(p40).subtract(p50).rename(['kvol0'])

        return [kvol, kvol0]

    def _correct_band(self, image, band_name, kvol, kvol0, f_iso, f_geo, f_vol):
        iso = ee.Image(f_iso)
        geo = ee.Image(f_geo)
        vol = ee.Image(f_vol)
        pred = vol.multiply(kvol).add(geo.multiply(kvol)).add(iso).rename(['pred'])
        pred0 = vol.multiply(kvol0).add(geo.multiply(kvol0)).add(iso).rename(['pred0'])
        cfac = pred0.divide(pred).rename(['cfac'])
        corr = image.select(band_name).multiply(cfac).rename([band_name])
        return corr

    def _apply(self, image, kvol, kvol0):
        f_iso = 0
        f_geo = 0
        f_vol = 0
        blue = self._correct_band(image, 'blue', kvol, kvol0, f_iso=0.0774, f_geo=0.0079, f_vol=0.0372)
        green = self._correct_band(image, 'green', kvol, kvol0, f_iso=0.1306, f_geo=0.0178, f_vol=0.0580)
        red = self._correct_band(image, 'red', kvol, kvol0, f_iso=0.1690, f_geo=0.0227, f_vol=0.0574)
        nir = self._correct_band(image, 'nir', kvol, kvol0, f_iso=0.3093, f_geo=0.0330, f_vol=0.1535)
        swir1 = self._correct_band(image, 'swir1', kvol, kvol0, f_iso=0.3430, f_geo=0.0453, f_vol=0.1154)
        swir2 = self._correct_band(image, 'swir2', kvol, kvol0, f_iso=0.2658, f_geo=0.0387, f_vol=0.0639)
        return image.select([]).addBands([blue, green, red, nir, swir1, swir2])

    def _applyBRDF(self, image):
        date = image.date()
        footprint = ee.List(image.geometry().bounds().bounds().coordinates().get(0))
        angles = self.getsunAngles(date, footprint)
        sunAz = angles[0]
        sunZen = angles[1]

        viewAz = self.azimuth(footprint)
        viewZen = self.zenith(footprint)

        kval = self._kvol(sunAz, sunZen, viewAz, viewZen)
        kvol = kval[0]
        kvol0 = kval[1]
        result = self._apply(image, kvol.multiply(self.envs.PI), kvol0.multiply(self.envs.PI))

        return result

    def runModel(self, imageCollection):
        imageCollection = imageCollection.map(self._applyBRDF)
        print ("Process Update: BRDF correction done!", imageCollection.size().getInfo())
        return imageCollection