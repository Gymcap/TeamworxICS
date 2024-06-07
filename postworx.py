#!/usr/bin/python
# ^ Set to your python path and make this file executable to run this file like a binary
import configparser
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import dateutil.relativedelta
import pytz
import requests
from icalendar import Calendar, Event
from tabulate import tabulate


# Initialization of the Config and Dictionary Files
def init(): # Read Conf OR Touch Conf and Quit to allow user to customize conf
	# Use the root name of this script to name the ini file
	pyName = os.path.basename(__file__).split('.')[0] 
	config_file = f"{pyName}.ini"
	
	# Touch the config file if it doesn't exist, then quit to allow the user to fill out config
	if not configparser.ConfigParser().read(config_file): 
		config = configparser.ConfigParser()
		config.optionxform=str
		config['Login'] = {
			'teamworx': 'example.ct-teamworx.com',
			'username': 'example@email.com',
			'password': 'p@55w0rd'
		}
		config['Config'] = {
			'daysBefore': '30',
			'daysAfter': '30',
			'timezone': 'US/Eastern',
			'cullOldShifts': 'True'
		}
		config['Dependencies'] = {'Please ensure Python3 is installed to get pip': 'https://www.python.org/downloads/', 'Please run the following in a terminal:': 'pip install icalendar datetime tabulate requests pytz configparser pathlib'}
		
		# Write the config file and exit, as the script will fail without user configs
		with open(config_file, 'w') as f:
			config.write(f)
		print(f"Edit the {pyName}.ini file generated in this scripts directory.\nPlease also make sure the dependencies are installed.")
		quit()
		
	else: # If the config file exists, read it
		config = configparser.RawConfigParser()
		config.read(config_file)

		# Extract Variables
		login = config['Login']
		conf = config['Config']
		username, password, teamworx, daysBefore, daysAfter, tz, cullShiftsBoolean = [
		login['username'], 
		login['password'], 
		login['teamworx'], 
		int(conf['daysBefore']), 
		int(conf['daysAfter']),
		pytz.timezone(conf['timezone']),
		conf['cullOldShifts']
		]
		org = teamworx.split('.')[0].capitalize() # Setting Org Name
		# Calculate Date Range
		startDate = (datetime.now() - timedelta(days=daysBefore)).strftime('%Y-%m-%d')
		endDate = (datetime.now() + timedelta(days=daysAfter)).strftime('%Y-%m-%d')
	dictFile = ".shiftDictionary" 
	if not configparser.ConfigParser().read(dictFile): # Touch .shiftDictionary.ini if it doesnt exist
		dictionary = configparser.ConfigParser()
		dictionary['Shifts'] = {}
		dictionary['Coworkers'] = {}
		with open(dictFile, 'w') as f:
			dictionary.write(f)
	dictionary = configparser.ConfigParser()
	dictionary.sections()
	dictionary.read(dictFile)
	dictionary['Shifts'] = {}
	dictionary['Coworkers'] = {}
	return conf, pyName, username, password, teamworx, org, tz, startDate, endDate, dictionary, dictFile, cullShiftsBoolean
	#print(conf, pyName, username, password, teamworx, tz, startDate, endDate, dictionary, dictFile)

def readDictionary(dictionary, dictFile, laborDate, shiftID):
	dictionary.read(dictFile)
	coworkersOnShift = dictionary['Coworkers']
	coworkersOnShift = coworkersOnShift.get(f"{laborDate} - {shiftID}", 'none')
	return coworkersOnShift
	#print(coworkersOnShift)



# Requests to Teamworx
def getAuth(teamworx, username, password): # 🍪 Login to Teamworx and retrieve auth cookies for further requests

	login = {
		'username': username,
		'password': password
	}
	auth_url = f"https://{teamworx}/json/a/account/authorization"
	headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
	auth = requests.post(auth_url, headers=headers, data=login) # Teamworx shares their cookies with us :D 🍪
	return auth
	#print(auth)

def getSchedule(teamworx, startDate, endDate, authCookies): # Request the schedule for the date range chosen
	url = f"https://{teamworx}/json/e/schedule/get/forDateRange"
	dateRange = {
		'startDate': startDate,
		'endDate': endDate
	}
	response = requests.post(url, data=dateRange, cookies=authCookies) # 🍪
	scheduleBloated = json.loads(response.text)['result']['shifts']
	keep = ['laborDate', 'positionName', 'inTimeText', 'outTimeText', 'hours', 'scheduleShiftId', 'locationName']
	schedule = [{k: shift[k] for k in shift if k in keep} for shift in scheduleBloated]
	return schedule
	#print(schedule)

def getCoworkersOnShift(shiftID, laborDate, teamworx, authCookies):
	# Make a Request to Teamworx for the Coworkers who will be present during your Shift
	coworkershiftinfo = { # Assign Details for Coworker Shift Request
		'shiftId': (f'{shiftID}'),
		'laborDate': (f'{laborDate}')
	}
	coworkers = requests.get( # Request Coworkers for this Shift
		f"https://{teamworx}/json/e/schedule/shift/coworkers",
		params=coworkershiftinfo,
		cookies=authCookies # 🍪
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
	return(coworkersOnShift)
	#print(coworkersOnShift) by Request to Teamworx



# Cleaning, Formatting, and Assigning Shift Info to Variables and Dictionary Entries
def setShiftVars(shift, org):
	utc_tz = pytz.UTC
	location, position, shiftID, laborDate = [
	shift['locationName'].replace('_', f" {org}, "), # Grab the Location and mix in the Org name
	shift['positionName'], # Grab the Position
	shift['scheduleShiftId'], # Grab the ShiftID (to request coworker shifts)
	shift['laborDate'] # Grab the Day of the Shift
	]
		## Assign Time Variables
	hours = f"{int(float(shift['hours']))}h" # Convert %Hours to Raw Hours and add "h" (5.25 = 5h)
		# Subtract Raw Hours from %Hours and Multiply by 60 to get Raw Minutes (5.25 = .25)
	minutes = int(float((shift['hours'] - int(float(shift['hours']))) * 60))
	minutes = f"{minutes}m" if minutes else "" # Add "m" to Raw Minutes, or clear the var if 0 (5.25 = 15m)
	length = (f"{hours}{minutes}") # Combine the two for human readable length (5.25 = 5h15m) / (5.0 = 5h)
		# Convert Date and Times to iCal compatible formats, and adjust for config timezone
	inTime = datetime.strptime(f"{shift['laborDate']} {shift['inTimeText']}", '%Y-%m-%d %I:%M %p').astimezone(utc_tz)
	outTime = datetime.strptime(f"{shift['laborDate']} {shift['outTimeText']}", '%Y-%m-%d %I:%M %p').astimezone(utc_tz)
	return location, position, shiftID, laborDate, hours, minutes, length, inTime, outTime
	#print(location, position, shiftID, laborDate, hours, minutes, length, inTime, outTime)	

def readCoworkersOnShift(dictionary, dictFile, laborDate, shiftID):
	dictionary = configparser.ConfigParser()
	dictionary.sections()
	dictionary.read(dictFile)
	coworkersOnShift = dictionary['Coworkers']
	coworkersOnShift = coworkersOnShift.get(f"{laborDate} - {shiftID}", f"none for {laborDate} - {shiftID}")
	return(coworkersOnShift)
	#print(coworkersOnShift) from Dictionary

def saveCoworkersToDictionary(dictionary, dictFile, laborDate, shiftID, coworkersOnShift):
	dictionary.read(dictFile)
	dictionary.set('Coworkers', f"{laborDate} - {shiftID}", f"{coworkersOnShift}")
	with open(dictFile, 'w') as f:
		dictionary.write(f)
	#print('### Shift has passed, Saving to Dictionary ###')

def cullOldShiftsFromDictionary(dictionary, dictFile, startDate):
	count = 0
	dictionary.read(dictFile)
	# Check the whole Dictionary
	for allEntries in dictionary.sections():
		for (title, value) in dictionary.items(allEntries):
			keyDate = title.split(' - ')[0]
			# If any Entry has Expired the Date Range selected by the User 
			if keyDate < startDate:
				# Remove the Entry
				dictionary.remove_option(allEntries, title)	
				count += 1
	with open(dictFile, 'w') as f:
		dictionary.write(f)
	
	# If any Shifts were Removed, Print the Amount
	s = 's' if count != 1 else ''
	if count > 0: print(f"\n {count} Old Shift{s} Cleaned from {dictFile}")
	return()




# Terminal Output
def prettyShifts(howDidWeGetHere, org, shift, coworkersOnShift): # The BIG Print
	return(f"###### {howDidWeGetHere} Details for {org} Shift #{shift['scheduleShiftId']} ######\n [{shift['laborDate']}] - [{shift['positionName']}]: [{shift['inTimeText']}-{shift['outTimeText']}] [{shift['hours']} Hours]\n################# Coworkers this Shift #################\n{coworkersOnShift}\n\n")




# Building the ICS File
def initICS(org):
	cal = Calendar()
	cal.add('prodid', f"-//Scheduled Shifts//{org}//")
	cal.add('version', '2.0')
	return cal
	# Setup first lines of the .ics file

def addEventICS(cal, position, length, inTime, outTime, coworkersOnShift, location):
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
	return
	# For every shift, generate and ical event

def saveICS(cal, org):
	directory = Path.cwd() / 'Schedule'
	directory.mkdir(parents=True, exist_ok=True)
	save = open(os.path.join('Schedule', f'{org}.ics'), 'wb')
	save.write(cal.to_ical())
	save.close()
	saved = f"Your Schedule has been saved to:\n{directory}/{org}.ics"
	return(saved)
	# Write the generated .ics file



# Run
def main(): 
		##### Initialize #####
	conf, pyName, username, password, teamworx, org, tz, startDate, endDate, dictionary, dictFile, cullShiftsBoolean = init()
		### Request Auth Cookie ###
	authCookies = getAuth(teamworx, username, password).cookies
		### Request Schedule ###
	schedule = getSchedule(teamworx, startDate, endDate, authCookies)
	
		# Set the first lines of the .ics file
	cal = initICS(org)
		# For each Shift in the Schedule
	for shift in schedule:
			# Extract the information for this shift
		location, position, shiftID, laborDate, hours, minutes, length, inTime, outTime = setShiftVars(shift, org)
		
			# Look for coworkers attending this shift in the dictionary
		coworkersOnShift = readDictionary(dictionary, dictFile, laborDate, shiftID)
		
			# Is there a Dictionary Entry for this Shift?
		if coworkersOnShift == 'none':
			
			# If there is no entry then make a request
			coworkersOnShift = getCoworkersOnShift(shiftID, laborDate, teamworx, authCookies)
			print(prettyShifts("Requested", org, shift, coworkersOnShift))
			
		################ CURRENT LOGIC FOR REQUEST REDUCTION, SUBJECT TO CHANGE #################
			# Is this Shift Date in the Past?
			#if not laborDate >= datetime.today().strftime('%Y-%m-%d'): 
			if laborDate < datetime.today().strftime('%Y-%m-%d'): 
				# If Shift is in the past, save it to the dictionary
				saveCoworkersToDictionary(dictionary, dictFile, laborDate, shiftID, coworkersOnShift) # Save Coworkers to Dictionary
				
			# Or is this Shift in the Future?
			else:
				# If this Shift Date has not passed, do not save it.
				pass
				#print("### Shift Date hasn't passed yet, Not saving to Dictionary ###")
		#########################################################################################
		
		# Was this Shift found in the Dictionary?	
		else:
			
			# If this Shift was found in the Dictionary, then use the info found there
			coworkersOnShift = readCoworkersOnShift(dictionary, dictFile, laborDate, shiftID) # Read Coworkers from Dictionary
			print(prettyShifts("On-Disk", org, shift, coworkersOnShift))
			
			# Append this Shift to the .ics file
		addEventICS(cal, position, length, inTime, outTime, coworkersOnShift, location)
	
	
	print(saveICS(cal, org))
		
	if conf.getboolean('culloldshifts') == True:
		cullOldShiftsFromDictionary(dictionary, dictFile, startDate)



if __name__ == "__main__":
	main()
