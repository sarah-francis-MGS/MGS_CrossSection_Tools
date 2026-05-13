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
    mapview_surficial_stratlines = arcpy.GetParameterAsText(0)
    out_gdb = arcpy.GetParameterAsText(1)
    scratch_folder = arcpy.GetParameterAsText(2)
    sgpg = arcpy.GetParameterAsText(3)
    printit("Variables set with tool parameter inputs.")

else:
    mapview_surficial_stratlines = r'D:\Faribault_Local\script_testing_030526.gdb\mapview_surficial_stratlines_030526_3'
    out_gdb = r'D:\Faribault_Local\script_testing_030526.gdb'
    scratch_folder = r'D:\Faribault_Local\scratch'
    sgpg = r'D:\FaribaultSandModel\Run2_022326\unit_masks.gdb\sgpg'
    printit("Variables set with hard-coded parameters for testing.")


#%%
# 3 Set spatial reference
spatialref = arcpy.Describe(mapview_surficial_stratlines).spatialReference
if spatialref.name == "Unknown":
    print("!!ERROR!!: {0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(mapview_surficial_stratlines)))
else:
    print("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(mapview_surficial_stratlines)))

#%%
# 4 check for MapUnit field in stratlines and sgpg
FieldExists(mapview_surficial_stratlines, "MapUnit")
FieldExists(sgpg, "MapUnit")

#%%
# 5 define file name for output
month = toolstart.strftime("%m")
year = toolstart.strftime("%y")
day = toolstart.strftime("%d")
version = 1
datestring = month+day+year

stratline_sgpg_mismatch_mapview_lines = os.path.join(out_gdb, "stratline_sgpg_mismatch_mapview_lines" + "_" + datestring + "_" + str(version))
#if the file already exists (if it was already run today), change the number on the end
#run this while loop until it finds the last file name
while arcpy.Exists(stratline_sgpg_mismatch_mapview_lines):
    version = version + 1
    stratline_sgpg_mismatch_mapview_lines = os.path.join(out_gdb, "stratline_sgpg_mismatch_mapview_lines" + "_" + datestring + "_" + str(version))

scratch_gdb = os.path.join(scratch_folder, "scratch" + "_" + datestring + "_" + str(version) + ".gdb")
print("Scratch gdb will be {0}".format(scratch_gdb))
arcpy.env.overwriteOutput = True
arcpy.management.CreateFileGDB(scratch_folder, "scratch" + "_" + datestring + "_" + str(version) + ".gdb")

#define mapview surficial stratlines output name with the same date number
#mapview_surficial_stratlines = os.path.join(out_gdb, "mapview_surficial_stratlines_" + datestring + "_" + str(version))

print("Output line and polygon files will end with {0}".format(datestring + "_" + str(version)))

#%%
# 8 Prep for intersect
#once mapview stratlines are intersected with sgpg, we will need to know which MapUnit field
#comes from the stratlines and which comes from the sgpg

# create temp copy of sgpg to add MapUnit_sgpg field name to clarify that it's for the sgpg
print("Exporting temp copy of surficial polygons to scratch gdb.")
sgpg_temp = os.path.join(scratch_gdb, "sgpg_temp")
arcpy.conversion.ExportFeatures(sgpg, sgpg_temp)

#add fields and calculate them to equal MapUnit
print("Adding MapUnit_strat and MapUnit_sgpg fields.")
expression = "!MapUnit!"
arcpy.management.CalculateField(sgpg_temp, "MapUnit_sgpg", expression, '', '', 'TEXT')
arcpy.management.CalculateField(mapview_surficial_stratlines, "MapUnit_strat", expression, '', '', 'TEXT')

#delete MapUnit field from temp sgpg
print("Deleting MapUnit field from temp sgpg.")
arcpy.management.DeleteField(sgpg_temp, "MapUnit")

#%% 
# 9 Intersect mapview stratlines with sgpg
#then, we can see where the MapUnit_sgpg and MapUnit_strat fields are mismatched
intersect_temp = os.path.join(scratch_gdb, "intersect_temp")
arcpy.analysis.Intersect([mapview_surficial_stratlines, sgpg_temp], intersect_temp, '', '', 'LINE')

#export final mapview lines
#only export lines where MapUnit_strat =/= MapUnit_sgpg AND line segment is longer than 10 meters
print("Exporting mapview mismatch lines where MapUnit_strat is not equal to MapUnit_sgpg AND line segment is longer than 10 meters.")
where_clause = "{0} <> {1} And {2} > 10".format("MapUnit_sgpg", "MapUnit_strat", "Shape_Length")
arcpy.conversion.ExportFeatures(intersect_temp, stratline_sgpg_mismatch_mapview_lines, where_clause)

#%%
# 10 Buffer lines to make it easier to see in mapview
print("Buffering mismatch lines to make them easier to see in mapview.")
stratline_sgpg_mismatch_mapview_polys = os.path.join(out_gdb, "stratline_sgpg_mismatch_mapview_polys" + "_" +  datestring + "_" + str(version))
arcpy.analysis.Buffer(stratline_sgpg_mismatch_mapview_lines, stratline_sgpg_mismatch_mapview_polys, 10, '', 'FLAT')

#%%
# 11 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
