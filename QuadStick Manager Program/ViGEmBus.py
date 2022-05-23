#pyinstaller --onefile --console quadstickHID.spec

from pywinusb import hid
import traceback
import sys
import copy
import array
import qsflash
import queue
import threading
import ctypes


'''
Opens Virtual Game Emulator Bus DLL

opens a X360 or DS4 virtual emulator when needed to process updates from the Quadstick HID input

There are six possible update combinations, three quadstick usb modes x two virtual emulator modes.

'''

QUADSTICK_VENDOR_ID_OLD = 0x1fc9
QUADSTICK_PRODUCT_ID_OLD = 0x205B

QUADSTICK_VENDOR_ID = 0x16D0
QUADSTICK_PRODUCT_ID = 0x092B

HORI_VENDOR_ID = 0x0F0D
HORI_PRODUCT_ID = 0x0066

## Quadstick (native mode) USB report offsets

QS_BUTTONS  = 2
QS_LX       = 4
QS_LY       = 5
QS_RX       = 6
QS_RY       = 7
QS_RIGHT    = 8
QS_LEFT     = 9
QS_UP       = 10
QS_DOWN     = 11
QS_TRIANGLE = 12
QS_CIRCLE   = 13
QS_CROSS    = 14
QS_SQUARE   = 15
QS_L1       = 16
QS_R1       = 17
QS_L2       = 18
QS_R2       = 19

QS_ACCX     = 20
QS_ACCY     = 22
QS_ACCZ     = 24
QS_GYROX    = 26

## Quadstick X360CE USB report offsets

X360CE_LX   = 2
X360CE_LY   = 4
X360CE_RX   = 6
X360CE_RY   = 8
X360CE_L2   = 10
X360CE_R2   = 12
X360CE_BTNS = 13
X360CE_DPAD = 14

## Quadstick Dual Shock 4 mode USB report offsets

DS4_left_X  = 1
DS4_left_Y  = 2
DS4_right_X = 3
DS4_right_Y = 4

DS4_DPAD    = 5
		#unsigned int  ButtonState;    // Main buttons
		#unsigned int D_pad   : 4;
		#unsigned int square : 1; 4 0x10
		#unsigned int X      : 1; 5 0x20
		#unsigned int O      : 1; 6 0x40
		#unsigned int triangle : 1; 7 0x80
DS4_BUTTONS = 6
		#unsigned int L1     : 1; 0x01
		#unsigned int R1     : 1; 0x02
		#unsigned int L2     : 1; 0x04
		#unsigned int R2     : 1; 0x08
		#unsigned int select : 1; 0x10
		#unsigned int start  : 1; 0x20
		#unsigned int L3     : 1; 0x40
		#unsigned int R3     : 1; 0x80

DS4_HOME    = 7
		#unsigned int home   : 1; 0x01
		#unsigned int touch  : 1; 0x02
		#unsigned int count  : 6;

DS4_press_L2 = 8
DS4_press_R2 = 9

DS4_Power   = 12 #          // Battery status ? always 0 when plugged in

DS4_ACCX = 13 # & 14;  // X axis accelerometer Big Endian 0 - 1023
DS4_ACCZ = 15 # & 16;  // Z axis accelerometer Big Endian 0 - 1023
DS4_ACCY = 17 # & 18;  // Y axis accelerometer Big Endian 0 - 1023
DS4_GYROX     = 19 # & 20;  // X axis accelerometer Big Endian 0 - 1023
DS4_GYROZ     = 21 # & 22;  // Z axis accelerometer Big Endian 0 - 1023
DS4_GYROY     = 23 # & 24;  // Y axis accelerometer Big Endian 0 - 1023

DS4_T_pad_event    = 33 # : 4; //0x00 no data yet, 0x01 last touch data 0x02 moving
DS4_FINGER         = 36 #		uint8_t T_pad_finger_1[3];



DS4_BUTTON_L1 = 0x01
DS4_BUTTON_R1 = 0x02
DS4_BUTTON_L2 = 0x08
DS4_BUTTON_R2 = 0x01
DS4_BUTTON_select = 0x10
DS4_BUTTON_start  = 0x20
DS4_BUTTON_L3 = 0x40
DS4_BUTTON_R3 = 0x80

DS4_BUTTON_home = 0x01
DS4_BUTTON_touch = 0x02


XUSB_GAMEPAD_DPAD_UP = 0x0001
XUSB_GAMEPAD_DPAD_DOWN = 0x0002
XUSB_GAMEPAD_DPAD_LEFT = 0x0004
XUSB_GAMEPAD_DPAD_RIGHT = 0x0008
XUSB_GAMEPAD_START = 0x0010
XUSB_GAMEPAD_BACK = 0x0020
XUSB_GAMEPAD_LEFT_THUMB = 0x0040
XUSB_GAMEPAD_RIGHT_THUMB = 0x0080
XUSB_GAMEPAD_LEFT_SHOULDER = 0x0100
XUSB_GAMEPAD_RIGHT_SHOULDER = 0x0200
XUSB_GAMEPAD_GUIDE = 0x0400
XUSB_GAMEPAD_A = 0x1000
XUSB_GAMEPAD_B = 0x2000
XUSB_GAMEPAD_X = 0x4000
XUSB_GAMEPAD_Y = 0x8000

class VirtualGamepadEmulator(object):
    def __init__(self, mainWindow):
        print ("Initialize vbus")
        import vgamepad   # delay import to allow mainwindow transcript message if import fails
        self.vg = vgamepad
        self.emulated_controller_type = 0
        self.gamepad = None
        self.alive = None
        self._log = mainWindow.text_ctrl_messages.AppendText
        self._q = queue.Queue()
        self._qs_data = None
        self.DEBUG = None
        
        # when quadstick hid interface is opened the next two varibles will be assigned
        self.DS4_mode = False  # mode the quadstick is in
        self.X360CE_mode = False
        
        
    def open(self):
        #instanciate the desired type of emulated controller
        if qsflash.settings.get('enable_VGX', False):
            self.gamepad = self.vg.VX360Gamepad()
            self.emulated_controller_type = 1
            print('opened VX360Gamepad')
            self._log('opened virtual XBox gamepad\n')
        elif qsflash.settings.get('enable_VG4', False):
            self.gamepad = self.vg.VDS4Gamepad()
            # if self.DS4_mode:
                # self.gamepad.report = self.vg.win.vigem_commons.DS4_REPORT_EX()
            self.emulated_controller_type = 2
            print('opened VDS4Gamepad')
            self._log('opened virtual DS4 gamepad\n')
        else:
            #self._log('ViGEmBus not opened\n')
            self.emulated_controller_type = 0
        if self.gamepad:
            self.gamepad.reset()
            
    def close(self):
        if self.alive:
            self._log('closing virtual gamepad emulator\n')
        self.stop()
        self.emulated_controller_type = 0
        self.gamepad = None # this should close and delete the virtual gamepad
        
    def stop(self):
        self.alive = False
        
    def start(self):
        self.alive = True
        # enter console->serial loop
        self._thread = threading.Thread(target=self.updater)
        self._thread.daemon = True
        self._thread.start()
        print("started virtual gamepad thread")

    def update(self, qs_data): #array of data or None (to update touchpad press)
        #print('update: ', repr(qs_data))
        if self.alive:
            self._q.put(copy.copy(qs_data))
    
    def updater(self):
        print ("vigem updater thread started")
        qs_data = None
        try:
            while self.alive:
                qs_data = qs_data or self._q.get(True) # block waiting for new data from quadstick
                if qs_data: #if None, skip all but last part.  Allows sending None event to update touchpad Press
                    if self.emulated_controller_type == 1:  # emulating an xbox controller
                        if self.DS4_mode:
                            self.update_X360_with_PS4(qs_data)
                        elif self.X360CE_mode:
                            self.update_X360_with_X360CE(qs_data)
                        else:
                            self.update_X360_with_PS3(qs_data)
                    elif self.emulated_controller_type == 2: # emulating DS4 controller
                        if self.DS4_mode:
                            self.update_DS4_with_DS4(qs_data)
                        elif self.X360CE_mode:
                            self.update_DS4_with_X360CE(qs_data)
                        else:
                            self.update_DS4_with_PS3(qs_data)                        
                        
                #self._qs_data = qs_data # save off a copy for display update
                qs_data = None # if queue is empty, this will force blocking on the queue for next update
                if self._q.empty():  # update the display and block waiting for next update
                    #self.mainWindow.CallAfter(self.updateCells, *(self._qs_data,))
                    continue  # if no further updates available, go back and block waiting for one
                # we just sent an update and the queue is already holding one or more updates.
                # send the most recent and skip all the ones in between
                skipped = -1
                try:
                    while True:
                        qs_data = self._q.get(False)  # loop until empty exception thrown
                        skipped = skipped + 1
                except:
                    pass
                # qs_data may contain the next packet

                #print(self._write_report, self._write_report[0])
        except Exception as e:
            self.alive = False
            print('Exception in ViGEmBus thread: ', repr(e))
            print(traceback.format_exc())
            self._log('!!!!!! Exception in ViGEmBus updater thread !!!!!!')
            raise
            
            
    def unbuffered_update (self, qs_data):
        if self.DEBUG: self._log(repr(qs_data))
        try:
            if self.emulated_controller_type == 1:  # emulating an xbox controller
                if self.DS4_mode:
                    self.update_X360_with_PS4(qs_data)
                elif self.X360CE_mode:
                    self.update_X360_with_X360CE(qs_data)
                else:
                    self.update_X360_with_PS3(qs_data)
            elif self.emulated_controller_type == 2: # emulating DS4 controller
                if self.DS4_mode:
                    self.update_DS4_with_DS4(qs_data)
                elif self.X360CE_mode:
                    self.update_DS4_with_X360CE(qs_data)
                else:
                    self.update_DS4_with_PS3(qs_data)
        except Exception as e:
            print ('Unbuffered update exception:', repr(e))
            print(traceback.format_exc())
            self._log("Error in virtual gamepad update.  Restart QMP")



    def update_X360_with_PS3 (self, qs_data):  # QS not in PS4 boot mode
        #print (repr(qs_data))
        self.gamepad.report.sThumbLX  = (qs_data[QS_LX] << 8) - 32768
        if self.gamepad.report.sThumbLX == 0x7f00:
            self.gamepad.report.sThumbLX = 0x7fff

        self.gamepad.report.sThumbLY  = 32768 - (qs_data[QS_LY] << 8)
        if qs_data[QS_LY] == 0xff:
            self.gamepad.report.sThumbLY = 0x8000
        if qs_data[QS_LY] == 0:
            self.gamepad.report.sThumbLY = 0x7fff
            
        self.gamepad.report.sThumbRX  = (qs_data[QS_RX] << 8) - 32768
        if self.gamepad.report.sThumbRX == 0x7f00:
            self.gamepad.report.sThumbRX = 0x7fff
        
        self.gamepad.report.sThumbRY  = 32768 - (qs_data[QS_RY] << 8)
        if qs_data[QS_RY] == 0xff:
            self.gamepad.report.sThumbRY = 0x8000
        if qs_data[QS_RY] == 0:
            self.gamepad.report.sThumbRY = 0x7fff
        
        
        self.gamepad.report.bRightTrigger = qs_data[QS_R2]
        self.gamepad.report.bLeftTrigger = qs_data[QS_L2]
        
        buttons  = 0
        
        buttons |= XUSB_GAMEPAD_A if qs_data[QS_CROSS] > 0 else 0
        buttons |= XUSB_GAMEPAD_B if qs_data[QS_CIRCLE] > 0 else 0
        buttons |= XUSB_GAMEPAD_X if qs_data[QS_SQUARE] > 0 else 0
        buttons |= XUSB_GAMEPAD_Y if qs_data[QS_TRIANGLE] > 0 else 0
        
        buttons |= XUSB_GAMEPAD_LEFT_SHOULDER  if qs_data[QS_L1] > 0 else 0
        buttons |= XUSB_GAMEPAD_RIGHT_SHOULDER if qs_data[QS_R1] > 0 else 0
        buttons |= XUSB_GAMEPAD_LEFT_THUMB     if qs_data[QS_BUTTONS] & 0x04 else 0
        buttons |= XUSB_GAMEPAD_RIGHT_THUMB    if qs_data[QS_BUTTONS] & 0x08 else 0
        
        buttons |= XUSB_GAMEPAD_START if qs_data[QS_BUTTONS] & 0x02 else 0
        buttons |= XUSB_GAMEPAD_BACK  if qs_data[QS_BUTTONS] & 0x01 else 0
        buttons |= XUSB_GAMEPAD_GUIDE if qs_data[QS_BUTTONS] & 0x10 else 0
        
        buttons |= XUSB_GAMEPAD_DPAD_UP    if qs_data[QS_UP] > 0 else 0
        buttons |= XUSB_GAMEPAD_DPAD_DOWN  if qs_data[QS_DOWN] > 0 else 0
        buttons |= XUSB_GAMEPAD_DPAD_LEFT  if qs_data[QS_LEFT] > 0 else 0
        buttons |= XUSB_GAMEPAD_DPAD_RIGHT if qs_data[QS_RIGHT] > 0 else 0
        
        self.gamepad.report.wButtons = buttons

        self.gamepad.update()
        
    def update_X360_with_X360CE (self, qs_data):  # QS in X360CE mode
        #print (repr(qs_data))
        self.gamepad.report.sThumbLX  = (qs_data[X360CE_LX] << 8) - 32768
        if self.gamepad.report.sThumbLX == 0x7f00:
            self.gamepad.report.sThumbLX = 0x7fff

        self.gamepad.report.sThumbLY  = 32768 - (qs_data[X360CE_LY] << 8)
        if qs_data[X360CE_LY] == 0xff:
            self.gamepad.report.sThumbLY = 0x8000
        if qs_data[X360CE_LY] == 0:
            self.gamepad.report.sThumbLY = 0x7fff
            
        self.gamepad.report.sThumbRX  = (qs_data[X360CE_RX] << 8) - 32768
        if self.gamepad.report.sThumbRX == 0x7f00:
            self.gamepad.report.sThumbRX = 0x7fff
        
        self.gamepad.report.sThumbRY  = 32768 - (qs_data[X360CE_RY] << 8)
        if qs_data[X360CE_RY] == 0xff:
            self.gamepad.report.sThumbRY = 0x8000
        if qs_data[X360CE_RY] == 0:
            self.gamepad.report.sThumbRY = 0x7fff
        
        
        self.gamepad.report.bRightTrigger = qs_data[X360CE_R2]
        self.gamepad.report.bLeftTrigger = qs_data[X360CE_L2]
        
        buttons  = 0
        
        buttons |= XUSB_GAMEPAD_A if qs_data[X360CE_BTNS] & 0x02 else 0
        buttons |= XUSB_GAMEPAD_B if qs_data[X360CE_BTNS] & 0x04 else 0
        buttons |= XUSB_GAMEPAD_X if qs_data[X360CE_BTNS] & 0x01 else 0
        buttons |= XUSB_GAMEPAD_Y if qs_data[X360CE_BTNS] & 0x08 else 0
        
        buttons |= XUSB_GAMEPAD_LEFT_SHOULDER  if qs_data[X360CE_BTNS] & 0x10 else 0
        buttons |= XUSB_GAMEPAD_RIGHT_SHOULDER if qs_data[X360CE_BTNS] & 0x20 else 0
        buttons |= XUSB_GAMEPAD_LEFT_THUMB     if qs_data[X360CE_DPAD] & 0x01 else 0
        buttons |= XUSB_GAMEPAD_RIGHT_THUMB    if qs_data[X360CE_DPAD] & 0x02 else 0
        
        buttons |= XUSB_GAMEPAD_START if qs_data[X360CE_BTNS] & 0x40 else 0
        buttons |= XUSB_GAMEPAD_BACK  if qs_data[X360CE_BTNS] & 0x80 else 0
        buttons |= XUSB_GAMEPAD_GUIDE if qs_data[X360CE_DPAD] & 0x04 else 0
        
        dpad = qs_data[X360CE_DPAD] >> 3 #15 is off

        buttons |= XUSB_GAMEPAD_DPAD_UP    if (dpad < 2 or dpad ==7) else 0
        buttons |= XUSB_GAMEPAD_DPAD_DOWN  if (dpad > 2 and dpad < 6) else 0
        buttons |= XUSB_GAMEPAD_DPAD_LEFT  if (dpad > 4 and dpad < 8) else 0
        buttons |= XUSB_GAMEPAD_DPAD_RIGHT if (dpad > 0 and dpad < 4) else 0
        
        self.gamepad.report.wButtons = buttons

        self.gamepad.update()
    
    def update_X360_with_PS4 (self, qs_data):  # QS in PS4 boot mode
        #print (repr(qs_data))
        self.gamepad.report.sThumbLX  = (qs_data[DS4_left_X] << 8) - 32768
        if self.gamepad.report.sThumbLX == 0x7f00:
            self.gamepad.report.sThumbLX = 0x7fff

        self.gamepad.report.sThumbLY  = 32768 - (qs_data[DS4_left_Y] << 8)
        if qs_data[DS4_left_Y] == 0xff:
            self.gamepad.report.sThumbLY = 0x8000
        if qs_data[DS4_left_Y] == 0:
            self.gamepad.report.sThumbLY = 0x7fff
            
        self.gamepad.report.sThumbRX  = (qs_data[DS4_right_X] << 8) - 32768
        if self.gamepad.report.sThumbRX == 0x7f00:
            self.gamepad.report.sThumbRX = 0x7fff
        
        self.gamepad.report.sThumbRY  = 32768 - (qs_data[DS4_right_Y] << 8)
        if qs_data[DS4_right_Y] == 0xff:
            self.gamepad.report.sThumbRY = 0x8000
        if qs_data[DS4_right_Y] == 0:
            self.gamepad.report.sThumbRY = 0x7fff
        
        
        self.gamepad.report.bRightTrigger = qs_data[DS4_press_R2]
        self.gamepad.report.bLeftTrigger = qs_data[DS4_press_L2]
        
        buttons  = 0
        
        buttons |= XUSB_GAMEPAD_A if qs_data[DS4_DPAD] & 0x20 else 0
        buttons |= XUSB_GAMEPAD_B if qs_data[DS4_DPAD] & 0x40 else 0
        buttons |= XUSB_GAMEPAD_X if qs_data[DS4_DPAD] & 0x10 else 0
        buttons |= XUSB_GAMEPAD_Y if qs_data[DS4_DPAD] & 0x80 else 0
        
        buttons |= XUSB_GAMEPAD_LEFT_SHOULDER  if qs_data[DS4_BUTTONS] & 0x01 else 0
        buttons |= XUSB_GAMEPAD_RIGHT_SHOULDER if qs_data[DS4_BUTTONS] & 0x02 else 0
        buttons |= XUSB_GAMEPAD_LEFT_THUMB     if qs_data[DS4_BUTTONS] & 0x40 else 0
        buttons |= XUSB_GAMEPAD_RIGHT_THUMB    if qs_data[DS4_BUTTONS] & 0x80 else 0
        
        buttons |= XUSB_GAMEPAD_START if qs_data[DS4_BUTTONS] & 0x20 else 0
        buttons |= XUSB_GAMEPAD_BACK  if qs_data[DS4_BUTTONS] & 0x10 else 0
        buttons |= XUSB_GAMEPAD_GUIDE if qs_data[DS4_HOME] & 0x01 else 0
        
        buttons |= XUSB_GAMEPAD_DPAD_UP    if qs_data[DS4_DPAD & 0x0F] in (0,1,7) else 0
        buttons |= XUSB_GAMEPAD_DPAD_DOWN  if qs_data[DS4_DPAD & 0x0F] in (3,4,5) else 0
        buttons |= XUSB_GAMEPAD_DPAD_LEFT  if qs_data[DS4_DPAD & 0x0F] in (5,6,7) else 0
        buttons |= XUSB_GAMEPAD_DPAD_RIGHT if qs_data[DS4_DPAD & 0x0F] in (1,2,3) else 0
        
        self.gamepad.report.wButtons = buttons

        self.gamepad.update()
    
    def update_DS4_with_PS3 (self, qs_data):
        self.gamepad.report.bThumbLX  = qs_data[QS_LX]
        self.gamepad.report.bThumbLY  = qs_data[QS_LY]
        self.gamepad.report.bThumbRX  = qs_data[QS_RX]
        self.gamepad.report.bThumbRY  = qs_data[QS_RY]
        self.gamepad.report.bTriggerR = qs_data[QS_R2]
        self.gamepad.report.bTriggerL = qs_data[QS_L2]
        self.gamepad.report.wButtons  = (qs_data[QS_BUTTONS] << 8) #| qs_data[QS]
        #self.gamepad.report.bSpecial = qs_data[DS4_HOME]
        buttons  = 0
        
        buttons |= qs_data[3] & 0x0F  #dpad
        buttons |= qs_data[1] << 4  # square x o triangle l1 r1 l2 r2
        buttons |= (qs_data[2] & 0x1F) << 12
        
        self.gamepad.report.wButtons = buttons
              
        self.gamepad.update()
        
    def update_DS4_with_X360CE (self, qs_data):
        print ('update_DS4_with_X360CE: ', repr(qs_data))
        pass

    def update_DS4_with_DS4 (self, qs_data):
        #print (repr(qs_data))
        
        self.gamepad.report = self.vg.win.vigem_commons.DS4_REPORT_EX.from_buffer(bytearray(qs_data[1:] + [0,0,0,0,0,0,0,0,0]))
        #self.gamepad.report.ReportBuffer = bytes(qs_data[1:])
        self.gamepad.update_extended_report(self.gamepad.report)
        
        # self.gamepad.report.bThumbLX  = qs_data[DS4_left_X]
        # self.gamepad.report.bThumbLY  = qs_data[DS4_left_Y]
        # self.gamepad.report.bThumbRX  = qs_data[DS4_right_X]
        # self.gamepad.report.bThumbRY  = qs_data[DS4_right_Y]
        # self.gamepad.report.bTriggerR = qs_data[DS4_press_R2]
        # self.gamepad.report.bTriggerL = qs_data[DS4_press_L2]
        # self.gamepad.report.wButtons  = (qs_data[DS4_BUTTONS] << 8) | qs_data[DS4_DPAD]
        # self.gamepad.report.bSpecial = qs_data[DS4_HOME]
        
        # self.gamepad.update()
        
    # def updateCells(self, report):  # update the values in the cells on the voice control page
        # try:
            # for k in list(PS4IndexToCellMap.keys()):
                # r, c, name = PS4IndexToCellMap[k]
                # name = (name + '      ')[:8]
                # value = self._write_report[k]
                # string = '%s %+4d' % (name, value)
                # self.mainWindow.grid_1.SetCellValue(r, c, string)
                # color = (255,255,255)
                # if value != 0:
                    # color = (0,255,0)
                # self.mainWindow.grid_1.SetCellBackgroundColour(r, c, color)
            # self._update_errors = 0
        # except Exception as e:
            # print("updateCells ", repr(e))
            # self._update_errors += 1
            # if self._update_errors > 10:
                # self.stop()

# QS_BUTTONS  = 2
# QS_LX       = 4
# QS_LY       = 5
# QS_RX       = 6
# QS_RY       = 7
# QS_RIGHT    = 8
# QS_LEFT     = 9
# QS_UP       = 10
# QS_DOWN     = 11
# QS_TRIANGLE = 12
# QS_CIRCLE   = 13
# QS_CROSS    = 14
# QS_SQUARE   = 15
# QS_L1       = 16
# QS_R1       = 17
# QS_L2       = 18
# QS_R2       = 19

# QS_ACCX     = 20
# QS_ACCY     = 22
# QS_ACCZ     = 24
# QS_GYROX    = 26

# PS3IndexToCellMap = {
    # QS_TRIANGLE:(0,1,'TRIANGLE'),
    # QS_CIRCLE:(1,2,'CIRCLE'),
    # QS_SQUARE:(1,0,'SQUARE'),
    # QS_CROSS:(2,1,'CROSS'),
    # QS_UP:(4,1,'UP'),
    # QS_LEFT:(5,0,'LEFT'),
    # QS_RIGHT:(5,2,'RIGHT'),
    # QS_DOWN:(6,1,'DOWN'),
    # QS_R1:(8,2,'R1'),
    # QS_R2:(9,2,'R2'),
    # QS_R3:(10,2,'R3'),
    # QS_L1:(8,0,'L1'), 
    # QS_L2:(9,0,'L2'),
    # PS4_L3:(10,0,'L3'),
    # PS4_PS:(12,1,'PS'),
    # PS4_SHARE:(12,0,'SHARE'),
    # PS4_OPTIONS:(12,2,'OPTIONS'),
    # QS_RX:(14,2,'RX'),
    # QS_RY:(15,2,'RY'),
    # QS_LX:(14,0,'LX'),
    # QS_LY:(15,0,'LY'),
# }
# PS4IndexToCellMap = {
    # PS4_TRIANGLE:(0,1,'TRIANGLE'),
    # PS4_CIRCLE:(1,2,'CIRCLE'),
    # PS4_SQUARE:(1,0,'SQUARE'),
    # PS4_CROSS:(2,1,'CROSS'),
    # PS4_UP:(4,1,'UP'),
    # PS4_LEFT:(5,0,'LEFT'),
    # PS4_RIGHT:(5,2,'RIGHT'),
    # PS4_DOWN:(6,1,'DOWN'),
    # PS4_R1:(8,2,'R1'),
    # PS4_R2:(9,2,'R2'),
    # PS4_R3:(10,2,'R3'),
    # PS4_L1:(8,0,'L1'), 
    # PS4_L2:(9,0,'L2'),
    # PS4_L3:(10,0,'L3'),
    # PS4_PS:(12,1,'PS'),
    # PS4_SHARE:(12,0,'SHARE'),
    # PS4_OPTIONS:(12,2,'OPTIONS'),
    # PS4_RX:(14,2,'RX'),
    # PS4_RY:(15,2,'RY'),
    # PS4_LX:(14,0,'LX'),
    # PS4_LY:(15,0,'LY'),
# }
