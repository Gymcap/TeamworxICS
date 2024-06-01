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
# Use the name of this script to name the ini file
name = os.path.basename(__file__).split('.')[0] 
config_file = f"{name}.ini"

if not configparser.ConfigParser().read(config_file): # Touch the config file if it doesn't exist, then quit to allow the user to fill out config
    config = configparser.ConfigParser()
    config['Config'] = {'teamworx': 'example.ct-teamworx.com', 'username': 'example@email.com', 'password': 'p@55w0rd', 'timezone': 'US/Eastern'}
    config['Dependencies'] = {'Please ensure python is installed to get pip': 'https://www.python.org/downloads/', 'Please run the following in a terminal:': 'pip install icalendar datetime tabulate requests pytz configparser pathlib'}
    # Write the config file and exit, as the script will fail without user configs
    with open(config_file, 'w') as f:
        config.write(f)
    print(f"Edit the {name}.ini file generated in this scripts directory.\nPlease also make sure the dependencies are installed.")
    quit()
else: # If the config file exists, read it
    config = configparser.RawConfigParser()
    config.read(config_file)

conf = config['Config'] # Read Config
username = conf['username'] # Set your Username
password = conf['password'] # Set your Password
teamworx = conf['teamworx'] # Set your Teamworx link
org = teamworx.split('.')[0].capitalize() # Setting Org Name
tz = pytz.timezone(conf['timezone']) # Set your Timezone

login = { # Set the login information for the Request
    'username': username,
    'password': password
}

# Set the Date Range to One Month Before and After "Today"
startDate = (datetime.now() + relativedelta(months=-1)).strftime('%Y-%m-%d') # Set the start date to 1 Month before today
endDate = (datetime.now() + relativedelta(months=+1)).strftime('%Y-%m-%d') # Set the end date to 1 Month after today
schedule = []
dateRange = { # Set the Date Range for the Request
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

# Create .shiftDictionary
dictFile = f".shiftDictionary" 
if not configparser.ConfigParser().read(dictFile): # Touch .shiftDictionary.ini if it doesnt exist
	dictionary = configparser.ConfigParser()
	dictionary['Shifts'] = {}
	dictionary['Coworkers'] = {}
	with open(dictFile, 'w') as f:
		dictionary.write(f)
			
# Read .shiftDictionary
dictionary = configparser.ConfigParser()
dictionary.sections()
dictionary.read('.shiftDictionary')
dictionary['Shifts'] = {}
dictionary['Coworkers'] = {}

for shift in schedule:
		### Extract Variables
		## Assign Shift Variables
	location = shift['locationName'].replace('_', f" {org}, ") # Grab the Location and mix in the Org name
	position = shift['positionName'] # Grab the Position
	shiftID = shift['scheduleShiftId'] # Grab the ShiftID (to request coworker shifts)
	laborDate = shift['laborDate'] # Grab the Day of the Shift
	
		## Assign Time Variables
	hours = f"{int(float(shift['hours']))}h" # Convert %Hours to Raw Hours and add "h" (5.25 = 5h)
		# Subtract Raw Hours from %Hours and Multiply by 60 to get Raw Minutes (5.25 = .25)
	minutes = int(float((shift['hours'] - int(float(shift['hours']))) * 60))
	minutes = f"{minutes}m" if minutes else "" # Add "m" to Raw Minutes, or clear the var if 0 (5.25 = 15m)
	length = (f"{hours}{minutes}") # Combine the two for human readable length (5.25 = 5h15m) / (5.0 = 5h)
		# Convert Date and Times to iCal compatible formats, and adjust for config timezone
	inTime = datetime.strptime(f"{shift['laborDate']} {shift['inTimeText']}", '%Y-%m-%d %I:%M %p').astimezone(utc_tz)
	outTime = datetime.strptime(f"{shift['laborDate']} {shift['outTimeText']}", '%Y-%m-%d %I:%M %p').astimezone(utc_tz)
	
	# Check the dictionary for an entry for this shift
	dictionary.read('.shiftDictionary')
	coworkerDict = dictionary['Coworkers']
	coworkerDict = coworkerDict.get(f"{laborDate} - {shiftID}", 'none')
	if coworkerDict == 'none': # If no entry then Request Coworker Shifts ## If in the Past then Save Past Shifts to reduce future requests
		#print(f"### No Dictionary Entry for this Shift ###")
		
		# Make a Request to Teamworx for the Coworkers who will be present during your Shift
		coworkershiftinfo = { # Assign Details for Coworker Shift Request
			'shiftId': (f'{shiftID}'),
			'laborDate': (f'{laborDate}')
		}
		coworkers = requests.get( # Request Coworkers for this Shift
			f"https://{teamworx}/json/e/schedule/shift/coworkers",
			params=coworkershiftinfo,
			cookies=auth.cookies # 🍪
		)
		# Assign the coworker shift info to coworkers
		coworkers = json.loads(coworkers.text)['data']['shifts'] 
		
		for coworker in coworkers: # Combine stationName with postionName: Cashier: Dine Cashier 2
			coworkerPosition = coworker['positionName']
			coworkerStation = f": {coworker['stationName']}" if coworker['stationName'] else ""
			coworkerPositionStation = f"{coworkerPosition}{coworkerStation}"
			coworker['positionName'] = coworkerPositionStation
	
		# Clean up the Coworker Data
		coworkerKeep = ['employeeName', 'positionName', 'inTimeText', 'outTimeText'] # Values to be kept
		coworkers = [{k: shift[k] for k in shift if k in coworkerKeep} for shift in coworkers] # Filter out unwanted values and assign the finished list to coworkers
		coworkersOnShift = []
		coworkerSort = []
		for item in coworkers: # Sort coworker shifts in a Human Readable Way
			sorted_item = {key: item[key] for key in ['employeeName', 'inTimeText', 'outTimeText', 'positionName']}
			coworkerSort.append(sorted_item)
			
		# Tabulate coworkersOnShift so that it can be easily read in plaintext
		coworkersOnShift = (tabulate(coworkerSort, headers="firstrow", tablefmt="plain")).replace('None', '').replace('SAL Mgr, General', '## GM ##').replace('HR Mgr, Asst.', '# Manager #')
		coworkersOnShift = f"Coworkers:\n{coworkersOnShift}" # Label for Aesthetic, New-Line so the grid isn't disturbed'
		
		if not laborDate >= datetime.today().strftime('%Y-%m-%d'): # If Shift is in the past, save it to the dictionary
			#print('### Shift has passed, Saving to Dictionary ###')
			dictionary.read('.shiftDictionary')
			dictionary.set('Coworkers', f"{laborDate} - {shiftID}", f"{coworkersOnShift}")
			with open(dictFile, 'w') as f:
				dictionary.write(f)
		else: # Shift has not happened
			#print("### Shift hasn't happened yet, Not saving to Dictionary ###")
			pass
		
	else: # If there is an Entry, then this shift is probably in the past and probably won't change, so use the entry instead of requesting
		#print(f"### Shift is in Dictionary, Using Found Entry ###")
		dictionary = configparser.ConfigParser()
		dictionary.sections()
		dictionary.read('.shiftDictionary')
		coworkersOnShift = dictionary['Coworkers']
		coworkersOnShift = coworkersOnShift.get(f"{laborDate} - {shiftID}", f"none for {laborDate} - {shiftID}")
		
	# Print all the pertinent data for every requested shift into terminal
	print(f"########## Details for {org} Shift #{shift['scheduleShiftId']} ##########\n [{shift['laborDate']}] - [{shift['positionName']}]: [{shift['inTimeText']}-{shift['outTimeText']}] [{shift['hours']} Hours]\n################# Coworkers this Shift #################\n{coworkersOnShift}\n\n")
	
	# Append this Shift to the iCal file
	event = Event()
	event.add('name', "Work Time")
	event.add('summary', (f"{position}: {length}"))
	event.add('dtstart', inTime)
	event.add('dtend', outTime)
	event.add('description', f"{coworkersOnShift}")
	event.add('location', location)
	event.add('transp', "OPAQUE")
	event.add('dtstamp', inTime)
	event['uid'] = inTime
	event.add('priority', 5)
	cal.add_component(event)

directory = Path.cwd() / 'Schedule'
directory.mkdir(parents=True, exist_ok=True)
save = open(os.path.join('Schedule', f'{org}.ics'), 'wb')
save.write(cal.to_ical())
save.close()
print(f"Your Schedule has been saved to:\n{directory}/{org}.ics")



