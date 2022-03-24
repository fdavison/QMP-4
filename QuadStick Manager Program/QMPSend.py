import socket
import sys

UDP_IP = "127.0.0.1" #"0.0.0.0" #
UDP_PORT = 47807

def main():

    #print "QMP Sender ",

    try:
        qmp_url = None
        if len(sys.argv) > 1:
            SERIAL_PORT_SOCKET = socket.socket(socket.AF_INET, # Internet
                             socket.SOCK_DGRAM) # UDP
            SERIAL_PORT_SOCKET.sendto("\b" + sys.argv[-1] + "\r", (UDP_IP, UDP_PORT))
            #print "sent: ", sys.argv[-1]
    except Exception, e:
        print repr(e)
    sys.exit()
    
main()
