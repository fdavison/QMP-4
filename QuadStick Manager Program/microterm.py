from time import sleep, localtime
import serial
import threading
import queue
from serial.tools import list_ports
from qsflash import settings, save_repr_file

#import ConfigParser
#extension_dir = "c:\\NatLink\\NatLink\\Vocola\\extensions"
#ini_file = extension_dir + "\\quadstick.ini"

## create a serial connection to the quadstick to relay voice commands
RCV_TIMEOUT = 3.0

def has_serial_ports(): # return true if serial ports exist
    ports = list(list_ports.comports())
    print("Serial ports: ", repr(ports))
    return len(ports) > 0
    
class _Microterm(object):
    def __init__(self, mainWindow=None):
        print("init Microterm")
        self.mainWindow = None
        self.thread = None
        self.serial = None
        self.queue = queue.Queue() # used to transfer strings from listening thread to main window
        self.queue_flag = False # True when buffering a response
        self.update_thread = None
        self.update_buffer = queue.Queue()
        try:
            self.serial = self.find_quadstick_serial_port()
        except Exception as e:
            print("Microterm did not find port", repr(e))
            self.serial = None  #if no serial port, then disable most of this object
        self.mainWindow = mainWindow
        self.run = True
        if self.serial and self.mainWindow:
            self.log("Found a serial connection to QuadStick\n")
            # create a thread to display incoming characters on transcript
            self.thread = threading.Thread(target=self.transcript_listener)
            self.thread.setDaemon(True)
            self.thread.start()
            self.update_thread = threading.Thread(target=self.update_relay)
            self.update_thread.setDaemon(True)
            self.update_thread.start()
        
    def log(self, *args):
        # print messages on the program transcript
        if self.mainWindow:
            for arg in args:
                self.mainWindow.text_ctrl_messages.AppendText(str(arg))
            self.mainWindow.text_ctrl_messages.AppendText("\n")
        else:
            print(repr(args))

    def test_serial_port(self, port):
        try:
            print(( "testing ", port, " please wait...." ))
            try:
                ser = serial.Serial(port, 115200, timeout=2)
            except:
                print(( '*** unable to open serial port: ', port))
                raise
            ser.rtscts = False
            ser.xonxoff  = False
            ser.writeTimeout = 1
            try:
                sleep(2)
                ser.write("\rreset\r".encode())
            except:
                print(( '*** unable to write to serial port: ', port))
                raise
            try:
                x = ser.read(100).decode()          # read one hundred bytes
                print (repr(x))
                if x.find('all outputs reset') > 0:
                    self.log( 'Success!  Found a serial port for quadstick: ', port)
                    ser.timeout = 3.0 # lengthen timeout
                    return ser
                ser.close()
            except Exception as e:
                print( "read timeout on port ", port, repr(e))
                raise
        except:
            try:
                ser.close()
            except:
                pass
        return None

    def find_quadstick_serial_port(self):
        print("find serial connection to quadstick")
        # @todo: remember for next time
        ports = list(list_ports.comports())
        if not ports:
            return None
        port_names = [x[0] for x in ports]
        # check ini file for previous port selection
        try:
            old_port = None
            old_port = settings.get('com_port', None)
            #old_port = None
            print("old port: ", old_port)
            if old_port:
                ser = self.test_serial_port(old_port)
                if ser: return ser
        except Exception as e:
            print("reuse old port exception: ", repr(e))

        # try all serial ports in parallel....
        self.log( "scan for quadstick on ports: ", port_names)
        threads = [threading.Thread(target=self._test_port, args=(port,)) for port in port_names]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        #print "join complete ", repr(threads)
        if self.serial:
            print("port found: ", self.serial)
            return self.serial
        self.log( '*** Unable to find serial port connection to QuadStick ***')
        return None

    def _test_port(self, port_name):
        #print "test_port: ", port_name
        try:
            ser = self.test_serial_port(port_name)
            #print port_name, " result ", ser
            if ser:
                self.serial = ser
                settings['com_port'] = port_name
        except Exception as e:
            #print "test port exception: ", repr(e)
            pass
            
            
    def send(self, aString):
        print("microterm send: ", repr(aString))
        try:
            if self.serial: 
                #print repr(aString)
                self.serial.write(str(aString).encode())
                print("microterm serial write done")
            else: self.log( "\n*** no serial connection to quadstick ***\n" + aString)
            if not self.mainWindow:
                print("microterm no self.mainWindow")
                return self.read_response()
        except:
            self.log( "an error occurred while sending command")
            try:
                self.serial.close()
                self.log( " closed serial port ")
            except:
                self.log( " error while closing serial port ")
            try:
                self.log( " trying to re-open port ")
                self.serial = self.find_quadstick_serial_port()
                if self.serial:
                    self.log( "successfully reopened port")
                return ""
            except:
                self.log( " unable to recover from comm error.  Try restarting Dragon ")
        print("microterm send finished")
        return ""
            
    def sendline(self, aString):
        return self.send("\b%s\r" % (aString,))

    def read_response(self):
        answer = []
        while True:
            try:
                b = self.queue.get(True, RCV_TIMEOUT)
            except queue.Empty as e:
                break
            answer.append(b)
            if b[-1] == ">": # All responses from quadstick should end with > prompt
                print("prompt received")
                if self.queue.empty():
                    break
                if (len(b) > 1) and (b[-2] == "\n"):
                    break # don't wait for timeout when prompt received
        answer = "".join(answer)
        print(repr(answer))
        return answer
        
    def send_and_receive(self, aString):
        try:
            self.queue_flag = True  # temporarily queue up incoming character stream
            try:
                while self.queue.get(False): #drain the queue
                    pass
            except:
                pass # queue.get will throw an exception when empty
            self.send(aString)
            return self.read_response()
        finally:
            self.queue_flag = False

    def transcript_listener(self):
        #self.log("start listening for QuadStick responses\n")
        try:
            while self.run:
                response = []
                self.serial.timeout = None # switch to blocking
                response.append(self.serial.read(1))
                while self.serial.inWaiting():
                    self.serial.timeout = 0 # switch to non-blocking
                    response.append(self.serial.read(1024))
                try:
                    b = b"".join(response)
                    b = b.decode()
                except Exception as e:
                    b = str(e)
                if self.queue_flag:  # if something is waiting for a response
                    print("transcript listener: ", repr(b))
                    self.queue.put(b)
                elif self.mainWindow:
                    self.mainWindow.CallAfter(self.mainWindow.voice_transcript.AppendText, *(b,))
        except Exception as e:
            print("exception in transcript listener", repr(e))
 
    def read_qs_file(self, filename):
        if settings.get('enable_serial_port', True):
            aString = "\bread_file," + filename + "\r"
            return self.send_and_receive(aString)
        return ""

    def write_qs_file(self, filename, lines):
        # "write_file,0,name.csv\r" "write_file,1,line of text\n\r", "write_file,2,2017,2,9,12,34,56\r"
        if not settings.get('enable_serial_port', True): return None
        self.log("Downloading via serial connection: " + filename)
        aString = "\bwrite_file,0," + filename + "\r"
        print(self.send_and_receive(aString))
        sleep(.3)
        # join all the lines with \n and send them 512 bytes at a time
        blob = "\n".join(lines) + "\n"
        BLOBSIZE = 512
        while len(blob) > BLOBSIZE:
            line = blob[:BLOBSIZE]
            blob = blob[BLOBSIZE:]
            aString = "\bwrite_file,1," + line + "\r"  #  \n is line separator, \r runs command
            sleep(.1)
            print(self.send_and_receive(aString))
            self.mainWindow.text_ctrl_messages.AppendText(".")
            
        if len(blob) > 0:
            aString = "\bwrite_file,1," + blob + "\r"  
            print(self.send_and_receive(aString))
            sleep(.1)
        lt = localtime()
        aString = "\bwrite_file,2,"+ str(lt.tm_year - 2000) + "," + str(lt.tm_mon) + "," + str(lt.tm_mday) + "," + str(lt.tm_hour) + "," + str(lt.tm_min) + "," + str(lt.tm_sec) + "\r"
        self.log(" done")
        return self.send_and_receive(aString)

    def list_files(self):
        if self.serial is not None and settings.get('enable_serial_port', True):
            try:
                response = self.send_and_receive("\bfiles\r")
                print("Microterm.list_files: ", response)
                if response.find("FILES:") >= 0:
                    files = response.split()[2:-1]
                    print("Microterm.list_files: ", repr(files))
                    answer = []
                    for f in files:
                      answer.append((f, "", ""))
                    return answer
            except Exception as e:
                print("Exception in Microterm.list_files ", repr(e))
        return []
            
    def delete_file(self, filename):
        if self.serial is not None and settings.get('enable_serial_port', True):
            try:
                self.send_and_receive("\bdelete_file," + filename + "\r")
                return True
            except Exception as e:
                print("delete_file exception: ", repr(e))
        return None    

    def get_build(self):
        print("microterm get_build")
        try:
            if self.serial is not None and settings.get('enable_serial_port', True):
                return self.send_and_receive("\bbuild\r").split()[0]
        except Exception as e:
            print("get_build exception: ", repr(e))
        return None    

    def send_external_pointer_update(self, report):
        if self.serial is None: return
        try:
            report_list = ["USB",]
            for b in report:
                report_list.append(str(b))
            report_string = ",".join(report_list)
            self.update_buffer.put(report_string + "\r")
            #print "USB report: ", report_string
        except Exception as e:
            print("send_external_pointer_update: ", repr(e))

    def update_relay(self):  # if reports come in faster than they can be sent, skip to last report
        try:
            while self.run:
                report_string = self.update_buffer.get(True)  # block until an update shows up
                self.send(report_string)
                if self.update_buffer.empty():
                    continue  # if no further updates available, go back and block waiting for one
                # we just sent an update and the queue is already holding one or more updates.
                # send the most recent and skip all the ones in between
                report_string = None
                skipped = -1
                try:
                    while True:
                        report_string = self.update_buffer.get(False)  # loop until empty exception thrown
                        skipped = skipped + 1
                except:
                    pass
                #print " skipped: ", skipped
                if report_string:
                    self.send(report_string)
        except Exception as e:
            #self.log( "exception in update_relay" )
            print("exception in update_relay", repr(e))

    def close(self):
        global mt_singleton
        mt_singleton = None
        self.run = False
        try:
            self.serial.close()
            self.serial = None
        except:
            pass
        print("com port closed")

mt_singleton = None
def microterm(mainWindow=None):
    global mt_singleton
    if mt_singleton is None:
        print("create connection to quadstick")
        mt = _Microterm(mainWindow)
        if mt.serial:
            mt_singleton = mt        
    return mt_singleton
