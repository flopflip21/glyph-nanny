"""
Font
----
X duplicate unicode

Glyph
-----
X points at extreme
X unnecessary points
X contours overlapping in bad ways / too many contours
X open paths
X stray points
X unnecessay handles
- lines that are just off vertical or horizontal
X implied s curve
- crossed handles
X overlapping points on the same contour
X points just off vertical metric
- duplicate contours
X test unicode against agl

X the colors need to vary and perhaps the interface
  needs some sort or color indication. or, more text
  needs to be drawn.
X finish the interface and incorporate it into the observer
- use a representation factory for the report
"""

import math
from fontTools.misc.bezierTools import splitCubicAtT
from fontTools.agl import AGL2UV
from AppKit import *
import vanilla
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.roboFont import CurrentGlyph
from mojo.UI import UpdateCurrentGlyphView
from mojo.events import addObserver, removeObserver

# ------
# Colors
# ------

missingExtremaColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 1, 0, 0.75)
openContourColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0.5)
strayPointColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
smallContourColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 1, 0, 0.7)
textReportColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0.7, 0.3)
impliedSCurveColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0.8, 0, 0.85)
unnecessaryPointsColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
unnecessaryHandlesColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
overlappingPointsColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
pointsNearVerticalMetricsColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0.7, 0, 0.7)

# -------
# Palette
# -------

class OutlineTutorControls(BaseWindowController):

    def __init__(self):
        self.keysToControls = {}

        self.w = vanilla.FloatingWindow((185, 300))

        self.top = 10

        controls = [
            dict(key="unicodeValue", title="Unicode Value"),
            dict(key="contourCount", title="Contour Count")
        ]
        self.buildSettingsGroup("glyphChecks", "Glyph Checks", controls)

        controls = [
            dict(key="strayPoints", title="Stray Points"),
            dict(key="smallContours", title="Small Contours"),
            dict(key="openContours", title="Open Contours"),
            dict(key="extremePoints", title="Extreme Points"),
            dict(key="unnecessaryPoints", title="Unnecessary Points"),
            dict(key="unnecessaryHandles", title="Unnecessary Handles"),
            dict(key="overlappingPoints", title="Overlapping Points"),
            dict(key="pointsNearVerticalMetrics", title="Points Near Vertical Metrics"),
            dict(key="complexCurves", title="Complex Curves"),
        ]
        self.buildSettingsGroup("outlineChecks", "Outline Checks", controls)

        self.setUpBaseWindowBehavior()
        self.startObserver()

        self.settingsCallback(None)

        self.w.open()

    def windowCloseCallback(self, sender):
        self.stopObserver()

    def startObserver(self):
        self.observer = OutlineTutorObserver()
        addObserver(self.observer, "drawComments", "drawBackground")
        addObserver(self.observer, "drawComments", "drawInactive")

    def stopObserver(self):
        removeObserver(self.observer, "drawBackground")
        removeObserver(self.observer, "drawInactive")
        self.observer = None

    def buildSettingsGroup(self, groupID, title, items):
        tb = vanilla.TextBox((10, self.top, -10, 14), title, sizeStyle="small")
        l = vanilla.HorizontalLine((10, self.top + 18, -10, 1))
        setattr(self.w, groupID + "Title", tb)
        setattr(self.w, groupID + "Line", l)
        self.top += 24
        for item in items:
            key = item["key"]
            attr = key + "CheckBox"
            title = item["title"]
            default = item.get("default", True)
            cb = vanilla.CheckBox((10, self.top, -10, 18), title, value=default, sizeStyle="small", callback=self.settingsCallback)
            setattr(self.w, attr, cb)
            self.keysToControls[key] = cb
            self.top += 20
        self.top += 10

    def settingsCallback(self, sender):
        testStates = {}
        for key, cb in self.keysToControls.items():
            testStates[key] = cb.get()
        self.observer.setTestStates(testStates)
        UpdateCurrentGlyphView()

# ----------------
# Drawing Observer
# ----------------

class OutlineTutorObserver(object):

    def setTestStates(self, testStates):
        self.testStates = testStates

    def drawComments(self, info):
        glyph = info["glyph"]
        font = glyph.getParent()
        scale = info["scale"]
        report = getGlyphReport(font, glyph, self.testStates)
        # small contours
        d = report.get("smallContours")
        if d:
            self.drawSmallContours(d, scale)
        # points near vertical metrics
        d = report.get("pointsNearVerticalMetrics")
        if d:
            self.drawPointsNearVericalMetrics(d, scale)
        # implied S curves
        d = report.get("complexCurves")
        if d:
            self.drawComplexCurves(d, scale)
        # open contours
        d = report.get("openContours")
        if d:
            self.drawOpenContours(d, scale)
        # missing extremes
        d = report.get("extremePoints")
        if d:
            self.drawExtremePoints(d, scale)
        # stray points
        d = report.get("strayPoints")
        if d:
            self.drawStrayPoints(d, scale)
        # unnecessary points
        d = report.get("unnecessaryPoints")
        if d:
            self.drawUnnecessaryPoints(d, scale)
        # unnecessary handles
        d = report.get("unnecessaryHandles")
        if d:
            self.drawUnnecessaryHandles(d, scale)
        # overlapping points
        d = report.get("overlappingPoints")
        if d:
            self.drawOverlappingPoints(d, scale)
        # text report
        self.drawTextReport(report, scale)

    def drawSmallContours(self, contours, scale):
        smallContourColor.set()
        for contourIndex, box in contours.items():
            xMin, yMin, xMax, yMax = box
            w = xMax - xMin
            h = yMax - yMin
            r = ((xMin, yMin), (w, h))
            r = NSInsetRect(r, -5 * scale, -5 * scale)
            NSRectFillUsingOperation(r, NSCompositeSourceOver)
            x = xMin + (w / 2)
            y = yMin - (10 * scale)
            drawString((x, y), "Tiny Contour", 10, scale, smallContourColor)

    def drawOpenContours(self, contours, scale):
        openContourColor.set()
        for contourIndex, points in contours.items():
            start, end = points
            mid = calcMid(start, end)
            path = NSBezierPath.bezierPath()
            path.moveToPoint_(start)
            path.lineToPoint_(end)
            path.setLineWidth_(scale)
            path.setLineDash_count_phase_([4], 1, 0.0)
            path.stroke()
            drawString(mid, "Open Contour", 10, scale, openContourColor, backgroundColor=NSColor.whiteColor())

    def drawExtremePoints(self, contours, scale):
        path = NSBezierPath.bezierPath()
        d = 16 * scale
        h = d / 2.0
        o = 3 * scale
        for contourIndex, points in contours.items():
            for (x, y) in points:
                r = ((x - h, y - h), (d, d))
                path.appendBezierPathWithOvalInRect_(r)
                path.moveToPoint_((x - h + o, y))
                path.lineToPoint_((x + h - o, y))
                path.moveToPoint_((x, y - h + o))
                path.lineToPoint_((x, y + h - o))
                drawString((x, y - (16 * scale)), "Insert Point", 10, scale, missingExtremaColor)
        missingExtremaColor.set()
        path.setLineWidth_(scale)
        path.stroke()

    def drawStrayPoints(self, contours, scale):
        path = NSBezierPath.bezierPath()
        d = 20 * scale
        h = d / 2.0
        for contourIndex, (x, y) in contours.items():
            r = ((x - h, y - h), (d, d))
            path.appendBezierPathWithOvalInRect_(r)
            drawString((x, y - d), "Stray Point", 10, scale, strayPointColor)
        strayPointColor.set()
        path.setLineWidth_(scale)
        path.stroke()

    def drawComplexCurves(self, contours, scale):
        impliedSCurveColor.set()
        for contourIndex, segments in contours.items():
            for segment in segments:
                pt0, pt1, pt2, pt3 = segment
                path = NSBezierPath.bezierPath()
                path.moveToPoint_(pt0)
                path.curveToPoint_controlPoint1_controlPoint2_(pt3, pt1, pt2)
                path.setLineDash_count_phase_([0, 10 * scale], 2, 0.0)
                path.setLineWidth_(5 * scale)
                path.setLineCapStyle_(NSRoundLineCapStyle)
                path.stroke()
                mid = splitCubicAtT(pt0, pt1, pt2, pt3, 0.5)[0][-1]
                drawString(mid, "Complex Path", 10, scale, impliedSCurveColor, backgroundColor=NSColor.whiteColor())

    def drawUnnecessaryPoints(self, contours, scale):
        path = NSBezierPath.bezierPath()
        for contourIndex, points in contours.items():
            for pt in points:
                drawDeleteMark(pt, scale, path)
                x, y = pt
                drawString((x, y - (10 * scale)), "Unnecessary Point", 10, scale, unnecessaryPointsColor)
        unnecessaryPointsColor.set()
        path.setLineWidth_(2 * scale)
        path.stroke()

    def drawUnnecessaryHandles(self, contours, scale):
        unnecessaryHandlesColor.set()
        d = 10 * scale
        h = d / 2.0
        for contourIndex, points in contours.items():
            for bcp1, bcp2 in points:
                # line
                path1 = NSBezierPath.bezierPath()
                path1.moveToPoint_(bcp1)
                path1.lineToPoint_(bcp2)
                path1.setLineWidth_(3 * scale)
                path1.stroke()
                # dots
                path2 = NSBezierPath.bezierPath()
                for (x, y) in (bcp1, bcp2):
                    r = ((x - h, y - h), (d, d))
                    path2.appendBezierPathWithOvalInRect_(r)
                path2.setLineWidth_(scale)
                path2.stroke()
                # text
                mid = calcMid(bcp1, bcp2)
                drawString(mid, "Unnecessary Handles", 10, scale, unnecessaryHandlesColor, backgroundColor=NSColor.whiteColor())

    def drawOverlappingPoints(self, contours, scale):
        path = NSBezierPath.bezierPath()
        d = 10 * scale
        h = d / 2.0
        q = h / 2.0
        for contourIndex, points in contours.items():
            for (x, y) in points:
                r = ((x - d + q, y - q), (d, d))
                path.appendBezierPathWithOvalInRect_(r)
                r = ((x - q, y - d + q), (d, d))
                path.appendBezierPathWithOvalInRect_(r)
                drawString((x, y - (12 * scale)), "Overlapping Points", 10, scale, overlappingPointsColor)
        overlappingPointsColor.set()
        path.fill()

    def drawPointsNearVericalMetrics(self, verticalMetrics, scale):
        path = NSBezierPath.bezierPath()
        for verticalMetric, points in verticalMetrics.items():
            xMin = None
            xMax = None
            for (x, y) in points:
                path.moveToPoint_((x, y))
                path.lineToPoint_((x, verticalMetric))
                if xMin is None:
                    xMin = x
                elif xMin > x:
                    xMin = x
                if xMax is None:
                    xMax = x
                elif xMax < x:
                    xMax = x
            path.moveToPoint_((xMin, verticalMetric))
            path.lineToPoint_((xMax, verticalMetric))
        pointsNearVerticalMetricsColor.set()
        path.setLineWidth_(4 * scale)
        path.stroke()

    def drawTextReport(self, report, scale):
        text = []
        text += report.get("unicodeValue", [])
        text += report.get("contourCount")
        if text:
            text = "\n".join(text)
            x = 50
            y = 50
            drawString((x, y), text, 16, scale, textReportColor, alignment="left")

# Utilities

def drawDeleteMark(pt, scale, path):
    h = 6 * scale
    x, y = pt
    x1 = x - h
    x2 = x + h
    y1 = y - h
    y2 = y + h
    path.moveToPoint_((x1, y1))
    path.lineToPoint_((x2, y2))
    path.moveToPoint_((x1, y2))
    path.lineToPoint_((x2, y1))

def drawString(pt, text, size, scale, color, alignment="center", backgroundColor=None):
    attributes = attributes = {
        NSFontAttributeName : NSFont.fontWithName_size_("Lucida Grande", size * scale),
        NSForegroundColorAttributeName : color
    }
    if backgroundColor is not None:
        attributes[NSBackgroundColorAttributeName] = backgroundColor
    text = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
    x, y = pt
    if alignment == "center":
        width, height = text.size()
        x -= width / 2.0
        y -= height / 2.0
    text.drawAtPoint_((x, y))

def calcMid(pt1, pt2):
    x1, y1 = pt1
    x2, y2 = pt2
    x = x1 - ((x1 - x2) / 2)
    y = y1 - ((y1 - y2) / 2)
    return x, y

# --------
# Reporter
# --------

def getGlyphReport(font, glyph, testStates):
    tests = dict(
        unicodeValue=testUnicodeValue,
        contourCount=testContourCount,
        strayPoints=testForStrayPoints,
        smallContours=testForSmallContours,
        openContours=testForOpenContours,
        extremePoints=testForExtremePoints,
        unnecessaryPoints=testForUnnecessaryPoints,
        unnecessaryHandles=testForUnnecessaryHandles,
        overlappingPoints=testForOverlappingPoints,
        pointsNearVerticalMetrics=testForPointsNearVerticalMetrics,
        complexCurves=testForComplexCurves,
    )
    report = {}
    for key, test in tests.items():
        if testStates.get(key, True):
            report[key] = test(glyph)
        else:
            report[key] = None
    return report

# Glyph Data

def testUnicodeValue(glyph):
    """
    A Unicode value should appear only once per font.
    """
    report = []
    font = glyph.getParent()
    uni = glyph.unicode
    name = glyph.name
    # test against AGL
    expectedUni = AGL2UV.get(name)
    if expectedUni != uni:
        report.append("The Unicode value for this glyph may not be correct.")
    # look for duplicates
    if uni is not None:
        duplicates = []
        for name in sorted(font.keys()):
            if name == glyph.name:
                continue
            other = font[name]
            if other.unicode == uni:
                duplicates.append(name)
        report.append("The Unicode for this glyph is also used by: %s." % " ".join(duplicates))
    return report

# Glyph Construction

def testContourCount(glyph):
    """
    There shouldn't be too many overlapping contours.
    """
    report = []
    count = len(glyph)
    test = glyph.copy()
    test.removeOverlap()
    if count - len(test) > 2:
        report.append("This glyph has a unusally high number of overlapping contours.")
    return report

# Contours

def testForSmallContours(glyph):
    """
    Contours should not have an area less than or equal to 4 units.
    """
    smallContours = {}
    for index, contour in enumerate(glyph):
        box = contour.box
        if not box:
            continue
        xMin, yMin, xMax, yMax = box
        w = xMax - xMin
        h = yMin - yMax
        area = abs(w * h)
        if area <= 4:
            smallContours[index] = contour.box
    return smallContours

def testForOpenContours(glyph):
    """
    Contours should be closed.
    """
    openContours = {}
    for index, contour in enumerate(glyph):
        if not contour.open:
            continue
        start = contour[0].onCurve
        start = (start.x, start.y)
        end = contour[-1].onCurve
        end = (end.x, end.y)
        if start != end:
            openContours[index] = (start, end)
    return openContours

def testForExtremePoints(glyph):
    """
    Points should be at the extrema.
    """
    pointsAtExtrema = {}
    for index, contour in enumerate(glyph):
        dummy = glyph.copy()
        dummy.clear()
        dummy.appendContour(contour)
        dummy.extremePoints()
        testPoints = _getOnCurves(dummy[0])
        points = _getOnCurves(contour)
        if points != testPoints:
            pointsAtExtrema[index] = testPoints - points
    return pointsAtExtrema

def testForComplexCurves(glyph):
    """
    S curves are suspicious.
    """
    impliedS = {}
    for index, contour in enumerate(glyph):
        prev = _unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            if segment.type == "curve":
                pt0 = prev
                pt1, pt2 = [_unwrapPoint(p) for p in segment.offCurve]
                pt3 = _unwrapPoint(segment.onCurve)
                line1 = (pt0, pt3)
                line2 = (pt1, pt2)
                if index not in impliedS:
                    impliedS[index] = []
                if _intersectLines(line1, line2):
                    impliedS[index].append((prev, pt1, pt2, pt3))
            prev = _unwrapPoint(segment.onCurve)
    return impliedS

def testForUnnecessaryPoints(glyph):
    """
    Consecutive segments shouldn't have the same angle.
    """
    unnecessaryPoints = {}
    for index, contour in enumerate(glyph):
        for segmentIndex, segment in enumerate(contour):
            if segment.type == "line":
                prevSegment = contour[segmentIndex - 1]
                nextSegment = contour[(segmentIndex + 1) % len(contour)]
                if nextSegment.type == "line":
                    thisAngle = _calcAngle(prevSegment.onCurve, segment.onCurve)
                    nextAngle = _calcAngle(segment.onCurve, nextSegment.onCurve)
                    if thisAngle == nextAngle:
                        if index not in unnecessaryPoints:
                            unnecessaryPoints[index] = []
                        unnecessaryPoints[index].append(_unwrapPoint(segment.onCurve))
    return unnecessaryPoints

def testForOverlappingPoints(glyph):
    """
    Consequtive points should not overlap.
    """
    overlappingPoints = {}
    for index, contour in enumerate(glyph):
        if len(contour) == 1:
            continue
        prev = _unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            point = _unwrapPoint(segment.onCurve)
            if point == prev:
                if index not in overlappingPoints:
                    overlappingPoints[index] = set()
                overlappingPoints[index].add(point)
            prev = point
    return overlappingPoints

# Segments

def testForUnnecessaryHandles(glyph):
    """
    Handles shouldn't be used if they aren't doing anything.
    """
    unnecessaryHandles = {}
    for index, contour in enumerate(glyph):
        prevPoint = contour[-1].onCurve
        for segment in contour:
            if segment.type == "curve":
                pt0 = prevPoint
                pt1, pt2 = segment.offCurve
                pt3 = segment.onCurve
                lineAngle = _calcAngle(pt0, pt3, 0)
                bcpAngle1 = bcpAngle2 = None
                if (pt0.x, pt0.y) != (pt1.x, pt1.y):
                    bcpAngle1 = _calcAngle(pt0, pt1, 0)
                if (pt2.x, pt2.y) != (pt3.x, pt3.y):
                    bcpAngle2 = _calcAngle(pt2, pt3, 0)
                if bcpAngle1 == lineAngle and bcpAngle2 == lineAngle:
                    if index not in unnecessaryHandles:
                        unnecessaryHandles[index] = []
                    unnecessaryHandles[index].append((_unwrapPoint(pt1), _unwrapPoint(pt2)))
            prevPoint = segment.onCurve
    return unnecessaryHandles

# Points

def testForStrayPoints(glyph):
    """
    There should be no stray points.
    """
    strayPoints = {}
    for index, contour in enumerate(glyph):
        if len(contour) == 1:
            pt = contour[0].onCurve
            pt = (pt.x, pt.y)
            strayPoints[index] = pt
    return strayPoints

def testForPointsNearVerticalMetrics(glyph):
    """
    Points shouldn't be just off a vertical metric.
    """
    font = glyph.getParent()
    verticalMetrics = {
        0 : set()
    }
    for attr in "descender xHeight capHeight ascender".split(" "):
        value = getattr(font.info, attr)
        verticalMetrics[value] = set()
    for contour in glyph:
        for segment in contour:
            pt = _unwrapPoint(segment.onCurve)
            y = pt[1]
            for v in verticalMetrics:
                d = abs(v - y)
                if d != 0 and d <= 5:
                    verticalMetrics[v].add(pt)
    for verticalMetric, points in verticalMetrics.items():
        if not points:
            del verticalMetrics[verticalMetric]
    return verticalMetrics

# Utilities

def _getOnCurves(contour):
    points = set()
    for segement in contour:
        pt = segement.onCurve
        points.add((pt.x, pt.y))
    return points

def _unwrapPoint(pt):
    return pt.x, pt.y

def _intersectLines((a1, a2), (b1, b2)):
    # adapted from: http://www.kevlindev.com/gui/math/intersection/Intersection.js
    ua_t = (b2[0] - b1[0]) * (a1[1] - b1[1]) - (b2[1] - b1[1]) * (a1[0] - b1[0]);
    ub_t = (a2[0] - a1[0]) * (a1[1] - b1[1]) - (a2[1] - a1[1]) * (a1[0] - b1[0]);
    u_b  = (b2[1] - b1[1]) * (a2[0] - a1[0]) - (b2[0] - b1[0]) * (a2[1] - a1[1]);
    if u_b != 0:
        ua = ua_t / u_b;
        ub = ub_t / u_b;
        if 0 <= ua and ua <= 1 and 0 <= ub and ub <= 1:
            return a1[0] + ua * (a2[0] - a1[0]), a1[1] + ua * (a2[1] - a1[1])
        else:
            return None
    else:
        return None

def _calcAngle(point1, point2, r=None):
    width = point2.x - point1.x
    height = point2.y - point1.y
    angle = round(math.atan2(height, width) * 180 / math.pi, 3)
    if r is not None:
        angle = round(angle, r)
    return angle


if __name__ == "__main__":
    OutlineTutorControls()
