#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Check Surficial Geology Xsec Match
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: March 2026
'''
This script will take stratlines that were drawn in stacked cross-section
view and convert them to mapview. This is similar to the tool that
converts stratlines to mapview, except that this tool only converts
stratlines of the highest unit in each location, based on a unit list
text file. This tool then intersects surficial mapview stratlines
with surficial polygons, and exports mapview lines and polys in locations
where the mapunit does not match.
'''
# %% 
# 1 Import modules and define functions

import arcpy
import os
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    arcpy.AddMessage(message)
    print(message)

def printwarning(message):
    arcpy.AddWarning(message)
    print(message)
        
def printerror(message):
    arcpy.AddError(message)
    print(message)

# Define file exists function and field exists function

def FileExists(file):
    if not arcpy.Exists(file):
        printerror("Error: {0} does not exist.".format(os.path.basename(file)))
    #else: printit("{0} found.".format(os.path.basename(file)))
    
def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("Error: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

# Define function to check for geometry type

def correctGeometry(file, geometry1, geometry2):
    desc = arcpy.Describe(file)
    if not desc.shapeType == geometry1:
        if not desc.shapeType == geometry2:
            printerror("Error: {0} does not have {1} geometry.".format(os.path.basename(file), geometry1))
    #else: printit("{0} has {1} geometry.".format(os.path.basename(file), geometry))
# %% 
# 2 Set parameters to work in testing and compiled geopocessing tool

# !!!!!!!!!!!!!!!!!!!!!! 
#change the variable below if running in an IDE. 
# MAKE SURE TO CHANGE BACK TO "PRO" WHEN FINISHED
#----------------------------------------------------------------
#run_location = "ide"
run_location = "Pro"
#----------------------------------------------------------------
#!!!!!!!!!!!!!!!!!!!!!!

if run_location == "Pro":
    stratlines_mapview = arcpy.GetParameterAsText(0)
    unitlist_txt = arcpy.GetParameterAsText(1)
    out_gdb = arcpy.GetParameterAsText(2)
    scratch_folder = arcpy.GetParameterAsText(3)
    sgpg = arcpy.GetParameterAsText(4)
    printit("Variables set with tool parameter inputs.")

else:
    stratlines_mapview = r'D:\FaribaultSandModel\Run2_022326\SandModeling_TIN.gdb\stratlines_mapview'
    unitlist_txt = r'D:\Faribault_Local\unitlist2.txt'
    out_gdb = r'D:\Faribault_Local\script_testing_030526.gdb'
    scratch_folder = r'D:\Faribault_Local\scratch'
    sgpg = r'D:\FaribaultSandModel\Run2_022326\unit_masks.gdb\sgpg'
    printit("Variables set with hard-coded parameters for testing.")


#%%
# 3 Set spatial reference
spatialref = arcpy.Describe(stratlines_mapview).spatialReference
if spatialref.name == "Unknown":
    print("!!ERROR!!: {0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(stratlines_mapview)))
else:
    print("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(stratlines_mapview)))

#%%
# 4 check for MapUnit field in stratlines and sgpg
FieldExists(stratlines_mapview, "MapUnit")
FieldExists(sgpg, "MapUnit")

#%%
# 5 define file name for output
month = toolstart.strftime("%m")
year = toolstart.strftime("%y")
day = toolstart.strftime("%d")
version = 1
datestring = month+day+year

scratch_gdb = os.path.join(scratch_folder, "scratch_" + datestring + "_" + str(version)  + ".gdb")

#if the file already exists (if it was already run today), change the number on the end
#run this while loop until it finds the last file name
while arcpy.Exists(scratch_gdb):
    version = version + 1
    scratch_gdb = os.path.join(scratch_folder, "scratch_" + datestring + "_" + str(version)  + ".gdb")

print("Scratch gdb will be {0}".format(scratch_gdb))

scratch_gdb = os.path.join(scratch_folder, "scratch" + "_" + datestring + "_" + str(version) + ".gdb")
arcpy.env.overwriteOutput = True
arcpy.management.CreateFileGDB(scratch_folder, "scratch" + "_" + datestring + "_" + str(version) + ".gdb")

#define mapview surficial stratlines output name with the same date number
mapview_surficial_stratlines = os.path.join(out_gdb, "mapview_surficial_stratlines_" + datestring + "_" + str(version))

print("Mapview surficial stratline file will be {0}".format(mapview_surficial_stratlines))

#%%
# 6 set up unit list
printit("Creating unit list from text file.")
txt_file = open(unitlist_txt).readlines()
#create empty list for appending unit names
unitlist = []
#remove "\n" line break from each unit name and add to empty list
for units in txt_file:
    replace = units.replace("\n", "")
    unitlist.append(replace)
#remove extra spaces and tabs from list items
i = 0
while i < len(unitlist):
    unitlist[i] = unitlist[i].strip()
    i += 1
#remove blank list items
while '' in unitlist:
    unitlist.remove('')

#check for duplicates in unit list
def duplicatecheck(list):
    if len(set(list)) == len(list):
        printit("There are no duplicates in text file.") 
    else:
        printerror("!!ERROR!! Unit list has duplicates. Please edit to remove and then retry.") #add error
        
duplicatecheck(unitlist)

#%%
# 7 Create geometry and export mapview surficial stratlines

# #make copy of stratlines_mapview and call it "stratlines_mapview_working"
stratlines_mapview_working = os.path.join(scratch_gdb, "stratlines_mapview_working")
arcpy.env.overwriteOutput = True
arcpy.conversion.ExportFeatures(stratlines_mapview, stratlines_mapview_working)

print("Converting surficial stratlines to mapview.")
#loop thru unitlist from top to bottom. 
for unit in unitlist:
    print("Working on {0}.".format(unit))
    
    #export current unit lines from working lines to temp output
    #these are the lines from the current unit that do not have other overyling liens
    where_clause = "{0}='{1}'".format("MapUnit", unit)
    temp_unit_lines = os.path.join(scratch_gdb, "temp_lines_" + unit)
    arcpy.analysis.Select(stratlines_mapview_working, temp_unit_lines, where_clause)

    #use temp output to erase from working lines. Save as temp working.
    arcpy.env.overwriteOutput = True
    stratlines_mapview_working_erased = os.path.join(scratch_gdb, "stratlines_mapview_working_erased")
    arcpy.analysis.Erase(stratlines_mapview_working, temp_unit_lines, stratlines_mapview_working_erased)

    #merge erased working lines with temp unit lines.
    #save as new working lines, overwriting previous working lines
    arcpy.env.overwriteOutput = True
    arcpy.management.Merge([stratlines_mapview_working_erased, temp_unit_lines], stratlines_mapview_working)
    
#export copy of mapview stratlines
arcpy.env.overwriteOutput = True
arcpy.management.MultipartToSinglepart(stratlines_mapview_working, mapview_surficial_stratlines)


#%%
# 11 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))

# %%
