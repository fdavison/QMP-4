## Quadstick flash drive related functions

import os
import win32api
import csv
import wx

preferences = {}
defaults = {
    'joystick_deflection_minimum':'8',
    'joystick_deflection_maximum':'25',
    'deflection_multiplier_up':'140',
    'deflection_multiplier_down':'130',
    'deflection_multiplier_left':'100',
    'deflection_multiplier_right':'100',
    'joystick_D_Pad_inner':'25',
    'joystick_D_Pad_outer':'80',
    'sip_puff_threshold_soft':'8',
    'sip_puff_threshold':'40',
    'sip_puff_maximum':'70',
    'sip_puff_delay_soft':'1300',
    'sip_puff_delay_hard':'2400',
    'lip_position_minimum':'8',
    'lip_position_maximum':'35',
    'mouse_speed':'100',
    'volume':'40',
    'brightness':'75',
    'digital_out_1':'0',
    'digital_out_2':'0',
    'bluetooth_device_mode':'none',
    'bluetooth_authentication_mode':'4',
    'bluetooth_connection_mode':'pair',
    'bluetooth_remote_address':'',
    'enable_swap_inputs':'0',
    'enable_select_files':'1',
    'watchdog_disable':'0',
    'debug':'1',
    'joystick_dead_zone_shape':'1',
    'anti_dead_zone':'0',
    'enable_auto_zero':'0',
    'mouse_response_curve':'1',
    'enable_usb_comm':'0',
    'TIR_DeadZone':'0',
    'enable_DS3_emulation':'0',
    'enable_usb_a_host':'1',
    'titan_two':'0',
    }

# Local data storage for program data and game profile list

APPDATA = os.environ['APPDATA']

print ("APPDATA: ", APPDATA)

settings_file = APPDATA + "\\QMP_3_settings.repr"
old_settings_file = APPDATA + "\\quadstick_settings.repr"
settings = dict()

print("INITIALIZE QSFLASH SETTINGS")

def read_repr_file():
    global settings
    #print "read settings: ",
    try:
        f = open(settings_file, 'r')
        settings_string = f.read()
        #print ('settings ', repr(settings_string))
        f.close()
        settings.clear()  # modify existing dictionary
        settings.update(eval(settings_string))
    except Exception as e:
        print("read_repr_file exception: ", repr(e))
        try:
            f = open(old_settings_file, 'r')
            settings_string = f.read()
            #print settings_string
            f.close()
            settings.clear()  # modify existing dictionary
            settings.update(eval(settings_string))
            return settings
        except:
            print("no old repr file either")
            pass
        settings.clear() #return NEW blank dictionary
    #print ("Read settings file:  ", repr(settings))
    return settings

def save_repr_file(settings):
    f = open(settings_file, 'w')
    settings_string = repr(settings)
    #print ("save settings: ", settings_string)
    f.write(settings_string)
    f.flush()
    f.close()

QuadStickDrive = None
def find_quadstick_drive(force=None):
    #return None # for testing serial port functions
    global QuadStickDrive
    if force: QuadStickDrive = None  # force new search for drive
    if QuadStickDrive: return QuadStickDrive
    drives = win32api.GetLogicalDriveStrings()
    drives = drives.split('\000')[:-1]
    for d in drives:
        try:
            drive_name = win32api.GetVolumeInformation(d)[0]
            if drive_name.lower() == "quad stick":
                print("QuadStick drive letter: ", d)
                QuadStickDrive = d
                return d
        except:
            pass # try next drive
    return None

def load_preferences_file(mainWindow):
    global preferences
    d = find_quadstick_drive()
    if d is None:
        if mainWindow.microterm:
            #mainWindow.text_ctrl_messages.AppendText( "Searching for Bluetooth or serial connection... ")
            # try a serial connection if bluetooth ssp enabled
            #if preferences.get("bluetooth_device_mode") == "ssp":
            mt = mainWindow.microterm
            if mt.serial:
                prefs_file = mt.read_qs_file("prefs.csv")
                print("serial port preferences file contents:\n\n", len(prefs_file), repr(prefs_file))
                csvfile = prefs_file.split("\n")
                if len(csvfile) > 3: # at least three lines long
                    while csvfile[0].find("QuadStick Configuration") < 0:
                        csvfile.pop(0)
                if len(csvfile) > 3:
                    reader = csv.reader(csvfile, delimiter=',')
                    row_count = 0
                    for row in reader:
                        #print ', '.join(row) 
                        # skip header section
                        if row_count > 3 and row and row[0]: 
                            if row[0] == "**END OF FILE**":
                                break
                            if row[1]:
                                preferences[row[0]] = row[1]
                                print("assign ", row[0], " with ", row[1])
                        row_count += 1
                    return preferences
        #mainWindow.text_ctrl_messages.AppendText( "Serial connection not found.")
        return None
    pathname = d + 'prefs.csv'
    preferences.clear()
    preferences.update(defaults.copy()) # start out with defaults for any missing items
    try:
        with open(pathname.encode()) as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            row_count = 0
            for row in reader:
                #print ', '.join(row) 
                # skip header section
                if row_count > 3 and row and row[0] and row[1]:
                    preferences[row[0]] = row[1]
                row_count += 1
    except Exception as e:
        print('quadstick drive found but unable to read prefs.csv file')
        print(repr(e))
        return None
    #print repr(preferences)
    return preferences

CSV_HEADER = """QuadStick Configuration,Version 1.1
Preferences,,,,
prefs.csv,,,,
Preference,Value,Units,Description,
"""

def save_preferences_file(preferences):
    global QuadStickDrive
    QuadStickDrive = None # force refresh of quadstick drive
    d = find_quadstick_drive()
    if d is None:
        print("quadstick flash drive not found.  Try serial")
        # try a serial connection if bluetooth ssp enabled
        from microterm import microterm  # late import because microterm imports from this module
        mt = microterm()
        if mt.serial:
            lines = CSV_HEADER.splitlines()
            keys = list(preferences.keys())
            keys.sort()
            for key in keys:
                value = preferences[key]
                lines.append(key + "," + str(value) + ",,")
            for line in lines:
                print(line)
            resp = mt.write_qs_file("prefs.csv", lines)
            print("serial port preferences file bytes written: ", resp)
            if resp.find("bytes written") > -1:
                return True
        return None
    pathname = d + 'prefs.csv'
    try:
        os.remove(pathname)
    except:
        print('prefs.csv not found to delete')
    with open(pathname, 'w', newline='\r\n') as csvfile:
        # write header
        csvfile.write(CSV_HEADER)
        keys = list(preferences.keys())
        keys.sort()
        for key in keys:
            value = preferences[key]
            csvfile.write(key + ',' + str(value) + ',,\n') 
            # cannot use percent sign in wxGlade source files
        csvfile.flush()
        os.fsync(csvfile.fileno())
    return True

def save_csv_file(name, text):
    d = find_quadstick_drive()
    if d is None:
        print("quadstick flash drive not found")
        return None
    pathname = d + name
    try:
        os.remove(pathname)
    except:
        print('file not found to delete')
    with open(pathname, 'wb', 0) as csvfile:
        # write header
        csvfile.write(text)
        csvfile.flush()
        os.fsync(csvfile.fileno())
    return True

def list_quadstick_csv_files(mainWindow):  # quadstick flash drive
    mainWindow._csv_files = []
    d = find_quadstick_drive()
    if d is None:
        print("list_quadstick_csv_files, quadstick flash drive not found")
        if mainWindow.microterm:
            return mainWindow.microterm.list_files()
        return []
    print ('quadstick drive letter ', repr(d))
    for (paths, dirs, file_names) in os.walk(d):
        break #first level directory only is what we want
    csv_files = [n for n in file_names if (n.lower().find(".csv") > 0)] # only want .csv
    file_list = []
    #move default and prefs to front
    if "prefs.csv" in csv_files:
        file_list.append("prefs.csv")
        csv_files.remove("prefs.csv")
    if "default.csv" in csv_files:
        file_list.append("default.csv")
        csv_files.remove("default.csv")
    csv_files = sorted(csv_files, key=lambda s: s.lower())
    file_list.extend(csv_files)
    # read first line in each csv file and get spreadsheet id and name
    answer = []
    for name in file_list:
        spreadsheet_name = ""
        id = ""
        try:
            pathname = d + name
            print(repr(pathname))
            with open(pathname.encode()) as csvfile:
                firstline = csvfile.readline()
            parts = firstline.split(",")
            print(repr(parts))
            if parts[0] == "QuadStick Configuration":
                if parts[1] == "Version 1.4":
                    id = (parts[2].split("spreadsheets/d/")[1]).split("/")[0]
                    spreadsheet_name = parts[3]
                elif parts[1] == "Version 1.5":
                    id = parts[2]
                    spreadsheet_name = parts[3]
        except Exception as e:
            print("exception while reading details from csv files")
            print(repr(e))
        t = (name, id, spreadsheet_name)
        answer.append(t)
        print("CSV file: ", repr(t))
        mainWindow._csv_files.append({"id":id, "name":spreadsheet_name,"csv_name":name})
    return answer

def quadstick_drive_serial_number(mainWindow):
    # read boot sector from quadstick and pull out build number from serial number
    d = find_quadstick_drive()
    if d is None:
        print("quadstick flash drive not found")
        if mainWindow.microterm:
            #mainWindow.text_ctrl_messages.AppendText( "Searching for Bluetooth or serial connection... ")
            # try a serial connection if bluetooth ssp enabled
            #if preferences.get("bluetooth_device_mode") == "ssp":
            mt = mainWindow.microterm
            if mt.serial:
                build = mt.get_build()
                print("build number is: ", build)
                if build:
                    return int(build.strip())
        return None
    drive = os.open('\\\\.\\' + d[:2], os.O_RDONLY | os.O_BINARY)
    tmp = os.read(drive, 512) # read boot sector 
    #print (repr(tmp))
    #print tmp
    build = tmp[40] * 256 + tmp[39] #drive.read(2) # serial number
    sn = tmp[41] * 256 + tmp[42]
    #drive.close()
    print(repr(build), repr(sn))
    answer = build #ord(build[0]) + 256 * ord(build[1])
    if answer == 30867: #old firmware
        answer = 601
    return answer
