from ultrastik import ReportValue
import os, threading

class Mouse(object):
    def __init__(self, mainWindow, wx, QS, device_id=0):
        self._device_id = device_id # 0-2.  2 means two Ultrastiks, so no mouse
        self._id_offset = self._device_id * 4
        self.mainWindow = mainWindow
        self.wx = wx
        self.QS = QS

    def update_location(self, x, y, buttons):
        #print "update location: ", repr(xy)
        if self._device_id > 1:  # two active ultrastiks
            return
        # xy is mouse location on screen.  Convert to four unsigned ints relative to the center of the screen 0-100%
        
        #dead_zone = settings.get('TIR_DeadZone', 0)
        #sr = math.sqrt((x * x) + (y * y))
        # take +/- 0-100 and split into four +0-100
        ReportValue[0 + self._id_offset] = x if x >= 0 else 256 + x
        ReportValue[1 + self._id_offset] = y if y >= 0 else 256 + y
        bits = 0
        bit = 1
        for b in buttons:
            if b:
                bits = bits | bit
            bit = bit << 1
        ReportValue[2 + self._id_offset] = bits
        ReportValue[3 + self._id_offset] = 0
        if self.QS:
            #print "update location: ", repr(ReportValue)
            self.QS.send_feature_report(ReportValue)  # update the QuadStick USB inputs values
            #print "ReportValue: ", ReportValue

