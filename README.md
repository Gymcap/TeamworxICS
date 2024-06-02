# TeamworxICS  
### What is it  
This is a python script which requests shift data, and associated coworker shift data from [Teamworx](https://www.ct-teamworx.com/).  
It organizes this shift data into an iCalendar .ics file, which can then be imported or synced to calendars on various devices and services.  
It allows me to view my schedule in *my* calendar.


## First Run  
The script itself can be renamed.  
Upon first run, the script will generate an .ini file with the same root name as the script.  
The .ini file will be populated with some default values and some instructions to install dependencies.  
Replace the default values with your own, and run the script again.  
Upon a successful run, the script will create a folder called "Schedule" and place the generated .ics file within it.  

### What you will need :
- to Install 
> Python3 - https://www.python.org/downloads/  
> Dependencies - ```pip install icalendar datetime tabulate requests pytz configparser pathlib```  
  
- to Prepare
> a Teamworx link from your employer  
-> example.ct-teamworx.com  

> Your Username and Password  
-> example@email.com  
-> p@55w0rd  

> Your Timezone  
-> US/Eastern  


### Extra
This script can work as a binary, meaning you can run it like any other non-python binary.  
To enable this:
- Ensure that the first line points to the python binary installed on your computer:  
```#!/usr/bin/python```  
- Give the script executable permissions by either right-click>Permissions, or with:  
```chmod +x postworx.py```  
- After this I prefer to remove the .py file extension for aesthetic reasons, though it's not nessesary.  
```mv postworx.py postworx``` or ```cp postworx.py postworx```  
*replace 'postworx' with your script name if you renamed it*