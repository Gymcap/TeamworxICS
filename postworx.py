#!/usr/bin/python
# ^ Set to your python path and make this file executable to run this file like a binary
from icalendar import Calendar, Event, vCalAddress, vText
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from tabulate import tabulate
from pathlib import Path
import configparser
import requests
import time
import json
import pytz
import os
# Check if the config file exists
name = os.path.basename(__file__).split('.')[0] # Use the name of this script to name the ini file
config_file = f"{name}.ini"
if not configparser.ConfigParser().read(config_file):
    # If the config file doesn't exist, create a new one
    config = configparser.ConfigParser()
    
    # Add sections and options to the config file
    config['Config'] = {'teamworx': 'example.ct-teamworx.com', 'username': 'example@email.com', 'password': 'p@55w0rd', 'timezone': 'US/Eastern'}
    config['Dependencies'] = {'Please ensure python is installed to get pip': 'https://www.python.org/downloads/', 'Please run the following in a terminal:': 'pip install icalendar datetime tabulate requests pytz configparser pathlib'}
    
    # Write the config file and exit, as the script will fail without user configs
    with open(config_file, 'w') as f:
        config.write(f)
    print(f"Edit the {name}.ini file generated in this scripts directory.\nPlease also make sure the dependencies are installed.")
    quit()
else:
    # If the config file exists, read it
    config = configparser.RawConfigParser()
    config.read(config_file)

conf = config['Config'] # Read Config
username = conf['username'] # Set your Username
password = conf['password'] # Set your Password
teamworx = conf['teamworx'] # Set your Teamworx link
org = teamworx.split('.')[0].capitalize() # Setting Org Name
tz = pytz.timezone(conf['timezone']) # Set your Timezone
login = { # Set the username and password
    'username': username,
    'password': password
}
startDate = (datetime.now() + relativedelta(months=-1)).strftime('%Y-%m-%d') # Set the start date to 1 Month before today
endDate = (datetime.now() + relativedelta(months=+1)).strftime('%Y-%m-%d') # Set the end date to 1 Month after today
schedule = []
dateRange = { # Set the Date Range you want to request
    'startDate': startDate,
    'endDate': endDate
}
auth = requests.post( # Authenticate for a cookie 🍪
    f"https://{teamworx}/json/a/account/authorization",
    headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}, # One header nessesary for TSID1 cookie
    data=login
)
schedule = requests.post( # Request the Schedule for the Date Range
    f"https://{teamworx}/json/e/schedule/get/forDateRange",
    cookies=auth.cookies, # 🍪
    data=dateRange
)
schedule = json.loads(schedule.text)['result']['shifts'] # Assign the shift info to schedule
keep = ['laborDate', 'positionName', 'inTimeText', 'outTimeText', 'hours', 'scheduleShiftId', 'locationName'] # Values to be kept
schedule = [{k: shift[k] for k in shift if k in keep} for shift in schedule] # Filter out unwanted values and assign the finished list to schedule
# Prepare Calendar File
utc_tz = pytz.UTC
format_code = "%Y-%m-%d %I:%M %p"
cal = Calendar()
cal.add('prodid', f"-//Scheduled Shifts//{org}//")
cal.add('version', '2.0')	
for entry in schedule:
	location = entry['locationName'].replace('_', f" {org}, ") # Grab the Location and mix in the Org name
	position = entry['positionName'] # Grab the Position
	shiftid = entry['scheduleShiftId'] # Grab the ShiftID (to request coworker shifts)
	labordate = entry['laborDate'] # Grab the Day of the Shift
	coworkers = []
	coworkershiftinfo = { # Assign Details for Coworker Shift Request
		'shiftId': (f'{shiftid}'),
		'laborDate': (f'{labordate}')
	}
	coworkers = requests.get( # Request Coworkers for this Shift
		f"https://{teamworx}/json/e/schedule/shift/coworkers",
		params=coworkershiftinfo,
		cookies=auth.cookies # 🍪
	)
	coworkers = json.loads(coworkers.text)['data']['shifts'] # Assign the coworker shift info to coworkers
	
	# Combine stationName with postionName: Cashier: Dine Cashier 2
	for coworker in coworkers:
		position_name = coworker['positionName']
		station_name = f": {coworker['stationName']}" if coworker['stationName'] else ""
		combined_name = f"{position_name}{station_name}"
		coworker['positionName'] = combined_name
	
	print(coworkers)
	#time.sleep(9999)
	coworkerkeep = ['employeeName', 'positionName', 'inTimeText', 'outTimeText'] # Values to be kept
	coworkers = [{k: shift[k] for k in shift if k in coworkerkeep} for shift in coworkers] # Filter out unwanted values and assign the finished list to coworkers
	coworker_shifts = []
	coworker_sort = []
	for item in coworkers: # Sort coworker shifts in a Human Readable Way
		sorted_item = {key: item[key] for key in ['employeeName', 'inTimeText', 'outTimeText', 'positionName']}
		coworker_sort.append(sorted_item)
	
	# Tabulate coworker_shifts so that it can be easily read in plaintext
	coworker_shifts = (tabulate(coworker_sort, headers="firstrow", tablefmt="plain")).replace('None', '').replace('SAL Mgr, General', '## GM ##').replace('HR Mgr, Asst.', '# Manager #')
	# Print a preview of gathered information into the terminal window
	print(f"########## Details for {org} Shift #{entry['scheduleShiftId']} ##########\n [{entry['laborDate']}] - [{entry['positionName']}]: [{entry['inTimeText']}-{entry['outTimeText']}] [{entry['hours']} Hours]\n################# Coworkers this Shift #################\n{coworker_shifts}\n\n")
	
	# Assign Time Variables
	hours = f"{int(float(entry['hours']))}h"	
	minutes = int(float((entry['hours'] - int(float(entry['hours']))) * 60))
	minutes = f"{minutes}m" if minutes else ""
	length = (f"{hours}{minutes}")
	in_time = datetime.strptime(f"{entry['laborDate']} {entry['inTimeText']}", '%Y-%m-%d %I:%M %p').astimezone(utc_tz)
	out_time = datetime.strptime(f"{entry['laborDate']} {entry['outTimeText']}", '%Y-%m-%d %I:%M %p').astimezone(utc_tz)
	
	# Populate iCal Events
	event = Event()
	event.add('name', "Work Time")
	event.add('summary', (f"{position}: {length}"))
	event.add('dtstart', in_time)
	event.add('dtend', out_time)
	event.add('description', f"Coworkers:\n{coworker_shifts}")
	event.add('location', location)
	event.add('transp', "OPAQUE")
	event.add('dtstamp', in_time)
	event['uid'] = in_time
	event.add('priority', 5)
	cal.add_component(event)

directory = Path.cwd() / 'Schedule'
directory.mkdir(parents=True, exist_ok=True)
save = open(os.path.join('Schedule', f'{org}.ics'), 'wb')
save.write(cal.to_ical())
save.close()
print(f"Your Schedule has been saved to:\n{directory}/{org}.ics")

