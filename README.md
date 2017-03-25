# hdhrepg2myth

The purpose of this software is to provide an approximately four-hour guide when watching live TV using MythTV.  You must own a compatible HDHomeRun device, and this program has been tested only with a HDHomeRun Prime with the program installed on Mythbuntu with MythTV 0.28.

### Installation and Usage

All channels should already be setup and usable in Mythfrontend.

Download the program by clicking on "release" in GitHub and selecting the latest release.

If the program has previously been installed and is running, stop the program before installing the new version.

Unzip the files to your home folder.

In your home folder, there must be the install file, hdhrepg2myth.cfg file, and the hdhrepg2myth folder.  The install and hdhrepg2myth.cfg files must be in your home folder and not a subfolder.

Open a terminal and type "sudo ./install" without the quotes.

After installation, the install file and hdhrepg2myth folder can be deleted from the home folder.

Open hdhrepg2myth.cfg with a text editor, change the values as needed, and save the file.  This file must remain in the home folder.  Replace the underscores in the backend ip address with numbers.  The port number will most likely not need to be changed, and it is recommended to keep the channel low value set to 2 or above. 

Edit the xmltvid values in the channel information section of mythweb/settings to match channel values.  For example, set the xmltvid values to 2, 3, 4, etc.

Start Mythfrontend, and go to "Setup", "System Event Handlers", "LiveTV started".  Type "/opt/hdhrepg2myth/hdhrepg2myth.py" without the quotes.  

### Known Issues

This program has not been tested with multiple HDHomeRun devices on the local network.

The backend status may report the benign message "mythfilldatabase ran but did not insert any new data into the Guide."  This may be false due to the program not inserting any data that is after data that has previously been inserted.  

The program first inserts data when live TV starts.  Pressing "i" or "info"  after tuning the first channel will, therefore, not show the epg info for what is currently on.  Switching the channel or showing the guide will show the info.

### Legal

This program is a modified version of the HDHomeRun Kodi add-on.  It has been modified for the purpose described above.  A copy of the GNU GPL license is included, and no warranty is expressed or implied.  This program may be copied, distributed and/or modified in accordance with the included license.  The license does not include the guide data.  Refer to Silicondust (https://forum.silicondust.com/forum/index.php) for the conditions under which the guide data can be used.  
