import os
import subprocess
import time


def execute_Script(site_path, site_name):
    start_time = time.time()
    print('executing '+ site_name)
    p = subprocess.Popen(os.path.join(site_path, "RemoteExecuteScriptSilent.exe"))
    # p.wait()
    time.sleep(120)
    print('finished executing ' + site_name+' time taken:\n')
    # measure time and show on console:
    print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
    path_winner=r"C:/Users/Administrator/AppData/Roaming/BrowserAutomationStudio/release/winner4marketsv2.1"
    name_winner="Winner"

    path_5dimes= r"C:/Users/Administrator/AppData/Roaming/BrowserAutomationStudio/release/5Dimesimroved.1"
    name_5dimes="5Dimes"

    path_expect=r"C:/Users/Administrator/AppData/Roaming/BrowserAutomationStudio/release/ExpektStandalone1hv5"
    name_expect="Expect"

    while True:
        execute_Script(path_winner,name_winner)
        # execute_Script(path_5dimes, name_5dimes)
        # execute_Script(path_expect, name_expect)
