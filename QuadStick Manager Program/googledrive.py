#from exceptions import *
import threading
import queue
import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import uuid
import os
import qsflash
import base64
import wx
import time
import traceback

## Google Drive related functions to find and read CSV and VCH/VCL files


#firmware_folder_url = "https://quadstick.s3.amazonaws.com/firmware/builds/"

firmware_json = "http://fwjson3.quadstick.com"
#firmware_json = "https://drive.google.com/uc?id=0B7MVckMP_1T0QVhtVlVJdjl4b2M&authuser=0&export=download"

# this is used for updating from 1.04 to 2.00.  
#games_folder_url = "https://quadstick.s3.amazonaws.com/configurations/QuadStick/"

folder_row_div_tag = '<div class="folder-row">'

#games_profile_list_spreadsheet = "http://B9BThNV1MJRXtzB9sFR.quadstick.com" 
factory_games_ids_list = "http://bvhbml89uymwxubx.quadstick.com" 

version_url = "http://qmp2version.quadstick.com"
#telemetery_url =  "https://script.google.com/a/macros/quadstick.com/s/AKfycbwdzab1ps7bvGlXKHnQKkDKqGJf_i5MmaN7sXhqrcj75Wt5dlE/exec"

#telemetery_url = "https://telemetry.quadstick.com"

VERSION = '4.00.02'

IDHASH = str(uuid.getnode())
print(VERSION, IDHASH)

def get_google_drive_file_by_id(id):  # return the contents of a regular file (vhc,csv,png,etc) from its id
    download_file_by_id_url = "https://drive.google.com/uc?id=%s&authuser=0&export=download"
    url = download_file_by_id_url % (id,)
    f = urllib.request.urlopen(url)
    bytes = f.read()
    return bytes

def get_google_folders_from(url):
    f = urllib.request.urlopen(url)
    page = f.read()
    # print "get_google_folders_from", repr(page)
    body = page.split("<body>")[1]
    rows = body.split(folder_row_div_tag)
    rows = [row for row in rows if (row.find("google-apps.folder") > 0)] # filter for folders, not direct files
    return rows

firmware_builds = []

def get_firmware_versions():
    if len(firmware_builds) == 0:
        try:
            try:
                f = urllib.request.urlopen(firmware_json, None, 5.0)
            except:
                f = urllib.request.urlopen(firmware_json, None, 5.0)
            json = f.read()
            #print("firmware json: ", repr(json))
            builds = eval(json)
            #print(repr(builds))
            qsflash.settings["builds"] = builds
        except:
            builds = qsflash.settings.get("builds")
            if builds is None: raise
        del firmware_builds[:]
        firmware_builds.extend(builds)
    return firmware_builds
    
# Check for update to this program
def check_for_newer_version(mainWindow):
    # put this on a separate thread so the program becomes responsive if the urlopen takes a long time
    t = threading.Thread(target=_check_for_newer_version, args=(mainWindow,))
    t.daemon = True
    t.start()

def _check_for_newer_version(mainWindow):
    try:
        print("check for newer QMP version")
        try:
            f = urllib.request.urlopen(version_url, None, 5.0) #firmware_folder_url + "version.ini")
        except:
            f = urllib.request.urlopen(version_url, None, 5.0)
        version = f.read().decode()
        print("version: ", version, VERSION)
        if version > VERSION:
            wx.CallAfter(mainWindow.text_ctrl_messages.AppendText, "A newer version of this program is available at QuadStick.com\r\nVisit http://quadstick.com/downloads\r\n") 
            
            # if it has been more than a week since the last time we asked
            print("last time declined qmp update ", qsflash.settings.get("declined_qmp_update", 0))
            if (time.time() > (qsflash.settings.get("declined_qmp_update", 0) + (86400 * 7))):
                confirm = wx.MessageDialog( mainWindow, "Download the new update?", caption="QMP Update available", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION | wx.STAY_ON_TOP )
                result = confirm.ShowModal()
                if result == wx.ID_YES:
                    import webbrowser
                    url = """https://www.quadstick.com/downloads/"""
                    webbrowser.open(url, new=2)
                    qsflash.settings["declined_qmp_update"] = 0 # if they don't follow through, ask again next time
                else: # they declined to update.  Ask again in a week
                    qsflash.settings["declined_qmp_update"] = time.time()
            
                return # don't inflict two dialog boxes on them

        print("latest version is: ", version)
        build = mainWindow.build_number_text.GetValue()
        telemetry_log('start&version=' + VERSION + '&firmware=' + build)
    except Exception as e:
        print("check_for_newer_version exception " + repr(e))
        print(traceback.format_exc())
    # check for firmware update
    if build == 'None':  # no point if checking if not plugged in
        return
    try:
        print("check firmware version")
        builds = get_firmware_versions()
        for bld in builds:
            b = int(bld.get("version",0))
            if b > int(build):
                if "TEST" in bld.get("comment"):
                    continue
                wx.CallAfter(mainWindow.text_ctrl_messages.AppendText, "A newer version of the firmware is available. Please update.\r\n") 
                print("last time declined firmware update ", qsflash.settings.get("declined_firmware_update", 0))
                if (time.time() > (qsflash.settings.get("declined_firmware_update", 0) + (86400 * 7))):
                    confirm = wx.MessageDialog( mainWindow, "Please install the new firmware update.", caption="Firmware Update available", style=wx.OK | wx.STAY_ON_TOP )
                    #confirm.OKLabel = "Close"
                    result = confirm.ShowModal()
                    qsflash.settings["declined_firmware_update"] = time.time()
                return
                
    except Exception as e:
        print("check for newer firmware exception " + repr(e))
        print(traceback.format_exc())
        
def telemetry_log(log_string):
    # put this on a separate thread so the program does not slow down for user
    t = threading.Thread(target=_telemetry_log, args=(log_string,))
    t.setDaemon(True)
    t.start()

def _telemetry_log(log_string):
    try:
        #print "_telemetry_log: ", log_string
        f = urllib.request.urlopen("https://telemetry.quadstick.com/exec?qmp=" + IDHASH + "&log=" + repr(log_string), None, 10.0) # append log entry
        version = f.read()
        #print "telemetry log result: ", version
    except Exception as e:
        print("telemetry log exception " + repr(e))

def get_spreadsheet_folder_ids(key):
    url = "https://drive.google.com/open?id=" + key + "&authuser=0"
    f = urllib.request.urlopen(url)
    page = f.read()
    body = page.split('<div class="flip-entries">')[1]
    rows = body.split('<script>')[0]
    rows = rows.split('id="entry-')[1:]
    ids = {}
    for row in rows:
        id, title = row.split('<div class="flip-entry-title">')
        id = id.split('"')[0]
        title = title.split('</div>')[0]
        ids[title] = id
    return ids
    
def test_get_spreadsheet_ids():
    print(repr(get_spreadsheet_folder_ids("0BwJQJADcHggka2htZ0FlM2FMdTQ")))
    

# def get_factory_game_files_list():
    # f = urllib2.urlopen(factory_games_ids_list)
    # json = f.read()
    # result = eval(json)
    # result.sort() #key=lambda x: x[0])
    # result = [{"name":element[0],"id":element[1], "csv_name":element[2]} for element in result] #convert to list of dicts
    # QMP.text_ctrl_messages.AppendText("Retrieved " + str(len(result))+ " game file ids\r\n") # game_name
    # #print repr(result)
    # return result

from operator import itemgetter

MaxActiveThreads = threading.Semaphore(1)

# From Public Quadstick Google Drive that holds game profiles, get list of game folders

# these are used to import old games from version 1.04 into 2.00  
def get_game_profiles(url, mainWindow):
    game_profiles = queue.Queue() #[] # get fresh list
    rows = get_google_folders_from(url)
    threads = [threading.Thread(target=get_game_profile, args = (game_profiles, row, url)) for row in rows]
    for t in threads:
        t.setDaemon(True)
        t.start()
    wx.Yield()
    for t in threads:
        wx.Yield()
        t.join()
    wx.Yield()
    # convert queue to list
    result = []
    while not game_profiles.empty():
        (game_name, folder, path, name, url) = game_profiles.get()
        print(game_name, folder, path, name, url)
        wx.Yield()
        result.append((game_name, folder, path, name, url))
    # sort the list by game_name
    result.sort() #key=lambda x: x[0])
    # display result
    mainWindow.text_ctrl_messages.AppendText("Processed " + str(len(result))+ " game and voice files\r\n") # game_name
    return result
# Read the list of CSV files found inside the game folders
def get_game_profile(game_profiles, row, url):
    MaxActiveThreads.acquire()
    try:
        link = row.split('<a href="')[1]
        folder_name = link.split("</a>")[0]
        path, game_name = folder_name.split('">')
        folder = path.split("/")[-1]
        print("get game profile: ", folder, game_name)
        folder = '%27'.join(folder.split("&#39;")) #fix apostrophe from html encoding to url encoding
        game_name = "'".join(game_name.split("&#39;"))
        print("URL ", url + folder)
        f = urllib.request.urlopen(url + folder)
        page = f.read()
        #print page
        body = page.split("<body>")[1] #get rid of everything before <body>
        rows = body.split('<a href="')
        rows = [row for row in rows if ((row.find(".csv") > 0) or (row.find(".vch") > 0) or (row.find(".vcl") > 0))] # filter for files
        print("number of rows: ", len(rows), len(page))
        for row in rows: # pull out the file name and path info
            link = row.split("</a>")[0] # gets rid of everything past close anchor tag
            #print "link ", link
            path, name  = link.split('">')
            #print "path ", path, " name ", name
            path = path.split('/')[-2:] # last part of the path is the game folder name and file name
            path = ('/').join(path)
            path = '%27'.join(path.split("&#39;")) #fix apostrophe encoding
            print(game_name,name, path)
            #index = len(game_profiles) 
            game_profiles.put((game_name, folder, path, name, url))
    except:
        print("something went wrong in get_game_profile")
        pass
    MaxActiveThreads.release()
            
def read_google_drive_file(path, url):
    f = urllib.request.urlopen(url + path)
    page = f.read()
    #print page
    return page
# end of import from old QMP

def get_factory_game_and_voice_files():
    for i in range(3):
        try:
            f = urllib.request.urlopen(factory_games_ids_list, None, 5.0)
            json = f.read()
            games, voices = eval(json)  # [games, voices]
            games = [{"name":element[0],"id":element[1], "csv_name":element[2]} for element in games] #convert to list of dicts
            voices = [{"name":element[0],"id":element[2], "file_name":element[1]} for element in voices] #convert to list of dicts
            qsflash.settings["games"] = games
            qsflash.settings["voices"] = voices
            return [games, voices]
        except Exception as e:
            print("Unable to get_factory_game_and_voice_files: ", repr(e))
    games = qsflash.settings.get("games", [])
    voices = qsflash.settings.get("voices", [])
    return [games, voices]
            
# def read_S3_file(path, url=games_folder_url):
    # f = urllib2.urlopen(url + path)
    # page = f.read()
    # #print page
    # return page

