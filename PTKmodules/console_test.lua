start = os.time()
for i=1000,1,-1 do 
    reaper.ShowConsoleMsg("An arbitrary message string\n") 
end
elapsed = os.time() - start
message = string.format("Wrote 1000 messages in %.4f seconds.", elapsed)
reaper.ShowConsoleMsg(message)

