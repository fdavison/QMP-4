#
# Installation instructions:
#
# If needed, install PIP:  https://pip.pypa.io/en/latest/installing.html
# and add /python2.7/scripts to the system path
#
# Install pyserial package:
# "pip install pyserial"
# then copy this file to:
# C:\NatLink\NatLink\Vocola\extensions\vocola_ext_quadstick.py
#

from time import sleep
import serial
from serial.tools import list_ports

import ConfigParser

import socket

UDP_IP = "127.0.0.1"
UDP_PORT = 47807

sock = socket.socket(socket.AF_INET, # Internet
                    socket.SOCK_DGRAM) # UDP

extension_dir = "c:\\NatLink\\NatLink\\Vocola\\extensions"
ini_file = extension_dir + "\\quadstick.ini"

## create a serial connection to the quadstick to relay voice commands
        
class Microterm(object):
    def __init__(self):
        try:
            self.serial = self.find_quadstick_serial_port()
        except:
            self.serial = None  #if no serial port, then disable most of this object
            
    def test_serial_port(self, port):
        try:
            print "testing: ", port
            try:
                ser = serial.Serial(port, 115200, timeout=2.0)
            except:
                print '*** unable to open serial port: %s' % (port,)
                raise
            ser.rtscts = False
            ser.xonxoff  = False
            ser.writeTimeout = 4
            try:
                sleep(5)
                ser.write("\rreset\r")
            except:
                print '*** unable to write to serial port: %s' % (port,)
                raise
            try:
                x = ser.read(100)          # read one hundred bytes
                #print repr(x)
                if x.find('all outputs reset') > 0:
                    print 'Success!  Found serial port for quadstick: ', port
                    ser.timeout = 3.0 # lengthen timeout
                    return ser
                ser.close()
            except:
                print "read timeout on port ", port
                raise
        except:
            try:
                ser.close()
            except:
                pass
        return None

    def find_quadstick_serial_port(self):
        #find serial connection to quadstick
        # @todo: remember for next time
        ports = list(list_ports.comports())
        port_names = [x[0] for x in ports]
        # check ini file for previous port selection
        try:
            old_port = None
            config = ConfigParser.RawConfigParser()
            config.read(ini_file)
            old_port = config.get('QuadStick', 'port')
            ser = self.test_serial_port(old_port)
            if ser: return ser
        except:
            print "unable to use previous port: ", old_port

        print "scan for quadstick on ports: ", port_names
        for port in port_names:
            ser = self.test_serial_port(port)
            if ser: 
                # save port in ini file for next time
                try:
                    config = ConfigParser.RawConfigParser()
                    config.add_section('QuadStick')
                    config.set('QuadStick', 'port', port)
                    with open(ini_file, 'wb') as configfile:
                        config.write(configfile)
                except:
                    print "unable to save port name for next time"
                return ser
        print '*** Unable to find serial port connection to QuadStick ***'
        return None
    
    def read_response(self):
        answer = []
        while True:
            b = self.serial.read(1)
            if not b: break # timeout
            answer.append(b)
            if b == ">": # All responses from quadstick should end with > prompt
                if (len(answer) == 1) and (self.serial.inWaiting() == 0):
                    break
                if (len(answer) > 1) and (answer[-2] == "\n") and (self.serial.inWaiting() == 0):
                    break # don't wait for timeout when prompt received
            if b == "\n": # transmit a line to the quadstick program
                sock.sendto("".join(answer), (UDP_IP, UDP_PORT))
                answer = []

        answer = "".join(answer)
        # send to quadstick program's listing socket
        sock.sendto(answer, (UDP_IP, UDP_PORT))
        return ""
            
    def send(self, aString):
        try:
            if self.serial: 
                self.serial.write(aString)
            else: print "*** no serial connection to quadstick ***"
            return self.read_response()
        except:
            print "an error occurred while sending command"
            try:
                self.serial.close()
                print " closed serial port "
            except:
                print " error while closing serial port "
            try:
                print " trying to re-open port "
                self.serial = self.find_quadstick_serial_port()
                if self.serial:
                    print "successfully reopened port"
                return ""
            except:
                print " unable to recover from comm error.  Try restarting Dragon "
            

        
    def sendline(self, aString):
        return self.send("\r%s\r" % (aString,))


print '\nQuadStick serial connection extension loaded.\n'

#term = Microterm()

debug = False

# Vocola function: QuadStick.sendAndRead
def sendAndRead(aString):
    sock.sendto(aString, (UDP_IP, UDP_PORT))
    if debug:
        print aString
    return ""

    #return term.sendline(aString)

# Vocola procedure: QuadStick.sendline
def sendline(aString):
    response = sendAndRead(aString)
    if debug:
        print response

# to satisfy 'functional context' situations when chaining commands
# Vocola function: QuadStick.sendlineFnc
def sendlineFnc(aString):
    sendline(aString)
    return "" 

# Vocola function: QuadStick.resetComPort
def resetComPort():
    try:
        term.serial.close()
        print " closed serial port "
    except:
        print " error while closing serial port "
    try:
        print " trying to re-open port "
        term.serial = term.find_quadstick_serial_port()
        if term.serial:
            return "\nsuccessfully reopened port\n"
        return "\nno com port found\n"
    except:
        pass
    return "\n unable to recover from comm error.  Try restarting Dragon \n"

# Vocola procedure: QuadStick.debug_on
def debug_on():
    global debug
    debug = True
    return "\nDebug on\n"
       
# Vocola procedure: QuadStick.debug_off
def debug_off():
    global debug
    debug = False
    return "\nDebug off\n"
       
if __name__ == "__main__":
    print sendAndRead("help")
    sleep(5)

    