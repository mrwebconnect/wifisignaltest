import urandom
import time
import network
import binascii
import urequests
import sys

def purge_local_log():
    local_log = open("locallog" , 'w') # open the file we want to send
    local_log.close()

def log_local(log_message="Empty"):
    local_log = open("locallog" , 'a') # open the file we want to send
    local_log.write(str(mothership_time) + " - " + log_message + "\n")
    local_log.close()

def check_for_work():

    work_response = urequests.get(mothership_addr + ":8080/work")
    work_response_parts = work_response.text.split("|")
    return int(work_response_parts[0]), work_response_parts[1]


def get_rssi(ssid):
    global wlan
    
    networks = wlan.scan()
    network_found = False
    rssi = "NotFound"
    for network in networks:
        if network[0].decode() == ssid:
            network_found = True
            rssi = network[3]
            break
    
    if rssi == "NotFound":
       log_local("Network not found during RSSI scan")
       
    return network_found, rssi


def terminate_program():
    global wlan
    
    log_local("Received terminate signal.")
    wlan.disconnect()
    wlan.active(False)
    sys.exit(0)


# Portions of this code regarding constructing a multipart mime post in micropything adapted from
# https://stackoverflow.com/questions/62423565/how-to-send-image-to-an-api-in-micropython-language/62424855#62424855
# since urequests does not seem to be able to do a multipart mime post.  Altered to support file and match server req for this test
def make_request(file_data=None):
    boundary = '---011000010111000001101001' 
    #boundary fixed instead of generating new one everytime

    def encode_file(field_name):  # prepares lines for the file
        filename = my_mac  # dummy name is assigned to uploaded file
        return (
            b'--%s' % boundary,
            b'Content-Disposition: form-data; name="%s"; filename="%s"' % (
                field_name, filename),
            b'', 
            file_data
        )

    lines = [] 
    if file_data:
        lines.extend(encode_file('files')) # adding lines of file
    lines.extend((b'--%s--' % boundary, b'')) # ending  with boundary

    body = b'\r\n'.join(lines) # joining all lines constitues body
    body = body + b'\r\n' # extra addtion at the end of file

    headers = {
        'content-type': 'multipart/form-data; boundary=' + boundary
        }  # removed content length parameter
    return body, headers  # body contains the assembled upload package


def upload_file(url, headers, data):  
    http_response = urequests.post(
        url,
        headers=headers,
        data=data
    )

#    print(http_response.status_code) # response status code is the output for request made
    
    if (http_response.status_code != 204 and http_response.status_code != 200):
        print('cant upload')
        #raise UploadError(http_response) line commneted out
    http_response.close()


# funtion below is used to set up the file / photo to upload
def send_file(body, headers): #  path and filename combined
    url = mothership_addr + ":8000/upload"
    upload_file(url, headers, body) # using function to upload to telegram


def construct_post(path_to_file):
    path = path_to_file   # this is the local path
    my_file = open(path , 'rb') # open the file we want to send
    my_file_data = my_file.read() # generate file in bytes
    my_file.close()
    body, headers  = make_request(my_file_data) # generate body to upload 
    headers = { 'content-type': "multipart/form-data; boundary=---011000010111000001101001" }
    return body, headers


def connect_to_network(ssid, key):
    global wlan
    
    log_local("Scanning for networks.  Batch:" + str(current_batch))
    
    try:
        networks = wlan.scan()
        if len(networks) != 0:
            network_found = False
            for network in networks:
                if network[0].decode() == ssid:
                    network_found = True
                    wlan.connect(ssid,key)
                    #wait upto 120 seconds for connect
                    timewaited = 0
                    while wlan.isconnected() == False and timewaited < 120:
                        time.sleep(5)
                        timewaited += 5
                        log_local("Waiting to connect.  Batch: " + str(current_batch))
                
                    break
        else:
            log_local("No networks were found during scan")
    except:
        print("error in connect")
        pass
    

def run_test_iteration():
    global mothership_time
    network_found, currentRSSI = get_rssi(project_SSID)

    if network_found:
        starttime = time.ticks_ms()
        send_file(body, headers)
        elapsed_time = time.ticks_diff(time.ticks_ms(),starttime)
        http_response = urequests.request(method="POST",url=mothership_addr + ":8080/metrics",data = str(my_mac) + "|" + str(current_batch) + "|" + str(elapsed_time) + "|" + str(currentRSSI) ,json=None,headers=[])
        mothership_time = http_response.text
        http_response.close()
    else:
        log_local("Network not found in list")

def create_test_file():
    #create file to transfer
    log_local("Writing test file")
    my_file = open(my_mac,"w")

    urandom.seed(time.time())
    x = 0
    while x < file_size:
      bytes_written=my_file.write(urandom.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'))
      x+=bytes_written

    my_file.close()
    log_local("Test file written")

def get_project_config():
    
    global monitor_period
    global file_size
    global test_time
    global terminate_batch
    global mothership_time
    
    # get test parameters from mothership
    config_response = urequests.get(mothership_addr + ":8080/config")
    log_local("Config response:" + config_response.text)
    config_parts = config_response.text.split("|")
    monitor_period = int(config_parts[0])
    file_size = int(config_parts[1])
    test_time = int(config_parts[2])
    terminate_batch = int(config_parts[3])
    mothership_time = config_parts[4]
    config_response.close()

def post_mac_for_tracking():
    http_response = urequests.request(method="POST",url=mothership_addr + ":8080/metrics",data = str(my_mac) + "|" + str(current_batch) + "|Network Checkin|" ,json=None,headers=[])
    http_response.close()


# network information and mothership address
project_SSID = "YOURSSID"
project_key = "YOURNETWORKKEY"
mothership_addr = "http://YOUR.SERVER.IP.ADDRESS"

# start a new local log file for this power cycle
purge_local_log()

monitor_period = 15 #seconds between checks
file_size = 25000 # size of file to send
test_time = 1800 # target runtime in seconds
mothership_time = 999999 #mothership time
start_batch = 0
current_batch = 0
terminate_batch = 99
my_mac = ""

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
my_mac = binascii.hexlify(wlan.config("mac")).decode()

log_local("Connecting to network in config")
connect_to_network(project_SSID,project_key)

if wlan.isconnected():
    log_local("Connected to network")
    get_project_config()
else:
    log_local("Could not connect for initial config")
    sys.exit(1)

create_test_file()

body, headers = construct_post(my_mac)
log_local("Upload post constructed")

wlan.disconnect()
while wlan.isconnected():
    log_local("Waiting to disconnect")
    time.sleep(5)

# Individual antenna test batches run now
log_local("Entering main test loop")

while wlan.isconnected() == False:

    try:
        connect_to_network(project_SSID,project_key)

        if wlan.isconnected() == True:
            post_mac_for_tracking()
        
            while wlan.isconnected() == True:
            
                new_batch, mothership_time = check_for_work()

                #shut down if it is terminate batch
                if new_batch == terminate_batch:
                    terminate_program()

                elif new_batch != current_batch:
                    log_local("Ending batch: " + str(current_batch) + " and starting batch: " + str(new_batch))
                    current_batch = new_batch
            
                    teststart = time.time()
            
                    while wlan.isconnected() == True:

                        cyclestart = time.time()
                        run_test_iteration()
                        time.sleep(monitor_period - (time.time() - cyclestart))

                        elapsed_time = time.time() - teststart
                
                        if elapsed_time > test_time:
                            log_local("Test batch complete")
                            break
            
                else:
                    #rest for 30 seconds and then check new batch
                    log_local("No New batch.  Current batch: " + str(current_batch))
                    time.sleep(30)
                
        else:
            log_local("Network disconnected.  Current batch is: " + str(current_batch) + " retrying")
   
    except:
        print("caught error")
        pass
    
wlan.active(False)
wlan.disconnect()
