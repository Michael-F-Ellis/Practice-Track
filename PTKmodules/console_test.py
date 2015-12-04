from reaper_python import *
import time
fp = open("/tmp/junk", 'w+')
start = time.time()
for i in range(1000):
    print >> fp, "An arbitrary message string\n" , 
    #RPR_ShowConsoleMsg("An arbitrary message string\n")
elapsed = time.time() - start
message = "Wrote 1000 messages in {} seconds.".format(elapsed)
RPR_ShowConsoleMsg(message)
import os, sys
RPR_ShowConsoleMsg("{}".format(sys.path))

        

