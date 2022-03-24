from time import sleep
from pywinusb import hid
from qsflash import settings
import math

ULTRASTIK_VENDOR_ID = 0xD209
ULTRASTIK_PRODUCT_ID_1 = 0x0501
ULTRASTIK_PRODUCT_ID_2 = 0x0511
ReportValue = [0,0,0,0,0,0,0,0]  # Shared between up to two Ultrastiks and/or the Mouse

class UltraStikHID(object):
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self._log = mainWindow.text_ctrl_messages.AppendText
        self._us = None
        self._qs_data_handler = None
        self._enabled = False

    def open(self, qs, device_id=0):
        try:
            self._device_id = device_id
            self._id_offset = device_id * 4
            for i in range(10):
                for self._PID in (ULTRASTIK_PRODUCT_ID_1, ULTRASTIK_PRODUCT_ID_2,):
                    ultrasticks = hid.HidDeviceFilter(vendor_id = ULTRASTIK_VENDOR_ID, product_id = (self._PID + device_id)).get_devices()
                    if len(ultrasticks) > 0: 
                        break
                self._us = ultrasticks[0] #throws exception if no ultrasticks found
                print("UltraStik found: ", self._us)
                self._report_count = 0
                self._us.open()
                if qs:
                    self._qs_data_handler = qs.send_feature_report
                #sleep(0.1)
                self._us.set_raw_data_handler(self.data_handler)
                sleep(0.2)
                if self._report_count > 0:
                    self.log( 'UltraStik 360 Joystick ' + str(device_id + 1) + ' interface successfully opened' )  #can't use %d format with wxglade
                    return self #indicates success to calling method
                sleep(1)
                self._us.close()
                self._us = None
                sleep(0.1)
                print("try ultrastik again: ", device_id + 1, i)
            self.log( '**** Failed to open UltraStik 360 Joystick ' + str(device_id + 1) + " Try closing program and re-opening ****" )  #can't use %d format with wxglade
        except Exception as e:
            print('UltraStik exception: ', repr(e))
            #don't say anything about it  
            #self.log( 'UltraStik Game Controller ' + str(device_id + 1) + ' is not connected to PC' )
        try:
            self._us.close() # attempt to close if error occurred after open
        except:
            pass
        return None
            
    def check_status(self):
        if self._us:
            print("UltraStick hid status: Active= ", self._us.is_active(), " Open= ", self._us_is_open(), " Plugged= ", self._us_is_plugged())

    def close(self):
        if self._us: 
            self._us.close()
            self._us = None

    def data_handler(self, data, new_handler=None):  # called when an update event happens in the UltraStik driver
        self._report_count += 1
        #print 'UltraStick: ', self._device_id + 1, repr(data)
        if new_handler:
            self._qs_data_handler = new_handler
            return
        if self._qs_data_handler and self._enabled:
            try:
                # convert to signed xy value.  minus is left or up
                if self._PID == ULTRASTIK_PRODUCT_ID_2:
                    x = data[1] - 128 # centered around 128 0 is full left, 255 is full right
                    y = data[2] - 128
                else:
                    # modify the data before passing along to the QuadStick
                    if data[1] > 127: #8-bit negative
                        x = data[1] - 256
                    else:
                        x = data[1]
                    if data[2] > 127:
                        y = data[2] - 256
                    else:
                        y = data[2]
                # convert two signed ints into unsigned byte
                dead_zone = settings.get('TIR_DeadZone', 0)
                sr = math.sqrt((x * x) + (y * y))
                if  sr >  dead_zone:
                    net_deflection = sr - dead_zone
                    ratio = net_deflection / sr
                    x = int(x * ratio)
                    y = int(y * ratio)
                    x = x if x < 100 else 100 # limit value range to +/- 100
                    x = x if x > -100 else -100
                    y = y if y < 100 else 100 
                    y = y if y > -100 else -100
                    # if negative, offset by 256 so value is unsigned postive
                    ReportValue[0 + self._id_offset] = x if x >= 0 else 256 + x
                    ReportValue[1 + self._id_offset] = y if y >= 0 else 256 + y
                ReportValue[2 + self._id_offset] = data[3]  # pass button data straight through
                ReportValue[3 + self._id_offset] = data[4]
                self._qs_data_handler(ReportValue)  # update the QuadStick USB inputs values
            except Exception as e:
                print(repr(e))

    def enable(self, flag=True):
        self._enabled = flag

    def disable(self):
        self._enable = False

    def __log_print(self, arg):
        print(arg, end=' ')
    def log(self, *args):
        for arg in args:
            self._log(str(arg))
        self._log("\n")
