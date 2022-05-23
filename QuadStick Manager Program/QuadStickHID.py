from pywinusb import hid
import traceback
import sys
import copy
import array

QUADSTICK_VENDOR_ID_OLD = 0x1fc9
QUADSTICK_PRODUCT_ID_OLD = 0x205B

QUADSTICK_VENDOR_ID = 0x16D0
QUADSTICK_PRODUCT_ID = 0x092B

HORI_VENDOR_ID = 0x0F0D
HORI_PRODUCT_ID = 0x0066

class QuadStickHID(object):
    def __init__(self, mainWindow, CM):
        print("Initialize QuadStick HID wrapper")
        self.mainWindow = mainWindow
        self._log = mainWindow.text_ctrl_messages.AppendText
        self._qs = None
        self._data_handler = None  # eventually set to CronusMax.update method to pump data to PCPROG port on CM
        self._enabled = False
        self._feature_report_value = None
        self._output_report_value = None
        self._old_data = None
        self._cm = CM

    def open(self, cm_updater):
        try:
            ids = ((QUADSTICK_VENDOR_ID, QUADSTICK_PRODUCT_ID), \
                   (QUADSTICK_VENDOR_ID, QUADSTICK_PRODUCT_ID+1,), \
                   (QUADSTICK_VENDOR_ID, QUADSTICK_PRODUCT_ID+2,), \
                   (QUADSTICK_VENDOR_ID_OLD, QUADSTICK_PRODUCT_ID_OLD),
                   (HORI_VENDOR_ID, HORI_PRODUCT_ID))
            quadsticks = []
            for (vendor_id, product_id) in ids:
                quadsticks = hid.HidDeviceFilter(vendor_id = vendor_id, product_id = product_id).get_devices()
                if quadsticks:
                    break #found a quadstick
            self._qs = quadsticks[0] # throws exception if no quadstick  @todo handle more or less than one device
            #print qs
            self._qs.open()
            self.log( 'QuadStick Game Controller interface successfully opened' )
            if product_id == (QUADSTICK_PRODUCT_ID+1):
                self.log( 'QuadStick is in X360CE mode.'  )
                self._cm.X360CE_mode = True
                #if int(preferences.get('enable_usb_comm', 0)) > 0:
                    #self.log( '**USB commands and CronusMax connection will not work in X360CE mode**' )
            elif (product_id == HORI_PRODUCT_ID or product_id == QUADSTICK_PRODUCT_ID+2):
                self.log( 'QuadStick is in PS4 mode')
                self._cm.DS4_mode = True # let CM object know reports will be for DS4.
            print('Open Quadstick.  VendorID: ' + hex(vendor_id) + ' PID: ' + hex(product_id))
            self._data_handler = cm_updater
            self._qs.set_raw_data_handler(cm_updater)
            
            #self._qs.set_raw_data_handler(self.data_handler)
            self._feature_report_value = None
            self._output_report_value = None
            return self
        except Exception as e:
            print("Open QuadStick HID exception: ", repr(e))
            traceback.print_exc(5, file=sys.stdout)
            self.log( 'QuadStick Game Controller is not connected to PC' )
            try:
                self._qs.close() # attempt to close if error occurred after open
            except:
                pass
            
        return None
            
    def check_status(self):
        if self._qs:
            self.log("quadstick hid status: Active= ", self._qs.is_active(), " Open= ", self._qs.is_opened(), " Plugged= ", self._qs.is_plugged())

    def close(self):
        if self._qs: 
            self._qs.close()
            self._qs = None

    def data_handler(self, data, new_handler=None):  # take data from QS and relay it to CM
        #print (".",)
        if new_handler:
            self._data_handler = new_handler
            return
        if self._data_handler and self._enabled:
            self._data_handler(data)

    def send_feature_report(self, data, retry=1):  # used to transmit ultrastik, trackir or mouse location data to the quadstick
        try:
            if self._qs is None: 
                if data == self._old_data:
                    # print "no change in report"
                    return
                self._old_data = copy.copy(data)
                if self.mainWindow.microterm:
                    self.mainWindow.microterm.send_external_pointer_update(data)  # use serial port instead of usb                  
                self.update_display(data)
                return
            if self._feature_report_value is None:
                r = self._qs.find_feature_reports()
                print("Feature Reports: ", repr(r))
                r = r[0]
                self._feature_report = r
                v = list(r.values())[0]
                self._feature_report_value = v
            old_value = self._feature_report_value.get_value()
            # make sure data is the right length
            data = (data + ([0] * len(old_value)))[:len(old_value)]
            if old_value != data:
                self._feature_report_value.set_value(data)
                self._feature_report.send()
                # print "send feature report: ", repr(data)
            if self._qs is None: return
            self.update_display(data)
                #self.close()
        except Exception as e:
            print("send_feature_report exception ", repr(e))
            try:
                if retry:
                    self.close()
                    self.open(self._data_handler)
                    self.send_feature_report(data, 0)
            except:
                print("send_feature_report retry failed")
            
    def update_display(self, data):
        try: # to update the display on the External Pointer tab
            if data[0] < 128: # positive value, moving to the Right
                self.mainWindow.TIR_LeftRight.SetValue(data[0])
                self.mainWindow.TIR_LeftLeft.SetValue(100) # bar graph % is always left-to-right
            else:
                self.mainWindow.TIR_LeftLeft.SetValue(100 - (256 - data[0]))
                self.mainWindow.TIR_LeftRight.SetValue(0)
            if data[1] < 128: # positive value, moving Down
                self.mainWindow.TIR_LeftUp.SetValue(0)
                self.mainWindow.TIR_LeftDown.SetValue(100 - data[1])
            else:
                self.mainWindow.TIR_LeftUp.SetValue(256 - data[1])
                self.mainWindow.TIR_LeftDown.SetValue(100)

            if data[4] < 128: # positive value, moving to the Right
                self.mainWindow.TIR_RightRight.SetValue(data[4])
                self.mainWindow.TIR_RightLeft.SetValue(100) # bar graph % is always left-to-right
            else:
                self.mainWindow.TIR_RightLeft.SetValue(100 - (256 - data[4]))
                self.mainWindow.TIR_RightRight.SetValue(0)
            if data[5] < 128: # positive value, moving Down
                self.mainWindow.TIR_RightUp.SetValue(0)
                self.mainWindow.TIR_RightDown.SetValue(100 - data[5])
            else:
                self.mainWindow.TIR_RightUp.SetValue(256 - data[5])
                self.mainWindow.TIR_RightDown.SetValue(100)
            self.mainWindow.TIR_LeftUp.Refresh()
            self.mainWindow.TIR_LeftLeft.Refresh()
            self.mainWindow.TIR_LeftRight.Refresh()
            self.mainWindow.TIR_LeftDown.Refresh()
            self.mainWindow.TIR_RightUp.Refresh()
            self.mainWindow.TIR_RightLeft.Refresh()
            self.mainWindow.TIR_RightRight.Refresh()
            self.mainWindow.TIR_RightDown.Refresh()
        except Exception as e:
            print('Exception in TIR widget update: ', repr(e))
    
    
    def send_output_report(self, data, retry=1):
        try:
            if self._output_report_value is None:
                rs = self._qs.find_output_reports()
                print("USB device output reports: ", repr(rs))
                r = rs[0]
                self._output_report = r
                vs = list(r.values())
                #print repr(vs)
                v = vs[0]
                self._output_report_value = v
                #print dir(self._output_report_value)
            old_value = self._output_report_value.get_value()
            #print "old value: ", repr(old_value)
            data = (data + ([0] * len(old_value)))[:len(old_value)] # outgoing size must match incoming size
            #print "new value: ", repr(data)
            self._output_report_value.set_value(data)
            self._output_report.send()
        except Exception as e:
            print("send_output_report ", repr(e))
            try:
                if retry:
                    self.close()
                    self.open(self._data_handler)
                    self.send_output_report(data, 0)
            except:
                print("send_output_report retry failed")

    def sendline(self, string):
        # send string in chunks of eight characters
        string = "\r" + string + "\r"
        tail = len(string) % 8
        if tail > 0:
            string = string + ("\0" * (8 - tail))
        bytes = array.array("B", string.encode())
        chunk = bytes[:8]
        while chunk:
            self.send_output_report(list(chunk))
            bytes = bytes[8:]
            chunk = bytes[:8]
            
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

