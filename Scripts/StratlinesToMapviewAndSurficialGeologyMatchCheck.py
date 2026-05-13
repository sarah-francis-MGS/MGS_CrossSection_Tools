#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Convert Stratlines to Map View
# Coded by Sarah Francis, Minnesota Geological Survey
# Created Date: March 2026
'''
This script converts cross section stratigraphy lines to map view and can check
for match with surficial geology if desired. Outputs are: stratlines in mapview
(all lines), surficial stratlines in mapview (only stratlines that reach the
surface), mapview line file showing areas where surficial geology and stratlines
do not match, and buffered polygon file showing these same areas. User can convert
the output polygons to stacked xsec view if desired.
'''

#%%
#  1 Import modules and define functions

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
    #parameters retrieved by geoprocessing tool
    xsln_file = arcpy.GetParameterAsText(0)
    strat_all_orig = arcpy.GetParameterAsText(1)
    unitlist_txt = arcpy.GetParameterAsText(2)
    out_gdb = arcpy.GetParameterAsText(3)
    scratch_folder = arcpy.GetParameterAsText(4)
    check_sgpg_match = arcpy.GetParameter(5)
    sgpg = arcpy.GetParameterAsText(6)#appears if above boolean is true
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln_file = r'D:\FaribaultSandModel\Run2_022326\SandModeling_TIN.gdb\xsln'
    strat_all_orig = r'D:\FaribaultSandModel\Run2_022326\SandModeling_TIN.gdb\all_strat_vertices'
    unitlist_txt = r'D:\Faribault_Local\unitlist2.txt'
    out_gdb = r'D:\Faribault_Local\script_testing_030626.gdb' 
    scratch_folder = r'D:\Faribault_Local\scratch'
    check_sgpg_match = True
    sgpg = r'D:\FaribaultSandModel\Run2_022326\unit_masks.gdb\sgpg'#appears if above boolean is true
    printit("Variables set with hard-coded parameters for testing.")

#%%
# 3 Define additional parameters and check that they exist

xsln_etid_field = 'et_id'
stratline_etid_field = 'et_id'
stratline_unit_field = 'MapUnit'

#FileExists(xsln_file)
#FileExists(strat_all_orig)
FieldExists(xsln_file, xsln_etid_field)
FieldExists(xsln_file, 'mn_et_id')
FieldExists(strat_all_orig, stratline_etid_field)
FieldExists(strat_all_orig, 'mn_et_id')
FieldExists(strat_all_orig, stratline_unit_field)
if check_sgpg_match:
    FieldExists(sgpg, "MapUnit")

#%% 
# 4 Set mapview spatial reference based on xsln file

spatialref = arcpy.Describe(xsln_file).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln_file)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln_file)))

#%% 
# 5 Create output file and add fields
arcpy.env.overwriteOutput = True

#create string with today's date
month = toolstart.strftime("%m")
year = toolstart.strftime("%y")
day = toolstart.strftime("%d")
#version number in case tool was already run today
version = 1
datestring = month+day+year

#define output file name with today's date
stratlines_mapview_name = "mapview_stratlines_" + datestring + "_" + str(version)
stratlines_mapview = os.path.join(out_gdb, stratlines_mapview_name)

#if the tool was already run today, this will change the final number (version) in the string
while arcpy.Exists(stratlines_mapview):
    version = version + 1
    stratlines_mapview_name = "mapview_stratlines_" + datestring + "_" + str(version)
    stratlines_mapview = os.path.join(out_gdb, stratlines_mapview_name)

printit("Creating empty output file {0}.".format(stratlines_mapview))
arcpy.management.CreateFeatureclass(out_gdb, stratlines_mapview_name, 'POLYLINE', '', '', '', spatialref)

output_fields = [[stratline_etid_field, 'TEXT'], [stratline_unit_field, 'TEXT'], ["mn_et_id", "TEXT"]]
arcpy.management.AddFields(stratlines_mapview, output_fields)

#create scratch gdb with same date/version string
scratch_gdb = os.path.join(scratch_folder, "scratch" + "_" + datestring + "_" + str(version) + ".gdb")
printit("Creating scratch gdb {0}".format(scratch_gdb))
arcpy.env.overwriteOutput = True
arcpy.management.CreateFileGDB(scratch_folder, "scratch" + "_" + datestring + "_" + str(version) + ".gdb")

#%% 
# 6 Convert stratline points to real xy

printit("Converting stratline vertex points to mapview and adding to output file.")

#loop through cross sections
with arcpy.da.SearchCursor(xsln_file, ['SHAPE@', xsln_etid_field, "mn_et_id"]) as xsln_cursor:
    for line in xsln_cursor:
        etid = line[1]
        mn_etid = line[2]
        printit("Working on xsln {0} lines.".format(etid))
        pointlist = []
        for vertex in line[0].getPart(0):
            # List vertices in xsln
            xsln_y = vertex.Y
            pointlist.append(xsln_y)
        if len(pointlist) > 2:
            printit("Warning: xsln {0} has more than 2 vertices. It may not be straight East/West, and points will not convert correctly".format(etid))
        #throw an error if xsln is not straight east/west
        first_y = pointlist[0]
        last_y = pointlist[-1]
        
        if first_y != last_y:
            printerror("Error: xsln {0} vertices do not have the same y coordinate. Points will not plot correctly.".format(etid))
        # y coordinate will be the same for every vertex in this xsln
        y = first_y
        where_clause = "{0}='{1}'".format(stratline_etid_field, etid)
        #search through strat vertex points along current xsln
        with arcpy.da.SearchCursor(strat_all_orig, ['SHAPE@', stratline_unit_field], where_clause) as strat_cursor:
            for stratline in strat_cursor:
                unit = stratline[1]
                line_pointlist = []
                for vertex in stratline[0].getPart(0):
                    x = vertex.X
                    #calculate mapview coordinates
                    #x coordinate stays the same
                    new_x = x
                    #y coordinate is the same as the xsln y coordinate
                    new_y = y
                    point = arcpy.Point(new_x, new_y)
                    line_pointlist.append(point)
                line_array = arcpy.Array(line_pointlist)
                line_geom = arcpy.Polyline(line_array, spatialref)
                with arcpy.da.InsertCursor(stratlines_mapview, ['SHAPE@', stratline_etid_field, stratline_unit_field, 'mn_et_id']) as out_cursor:
                    out_cursor.insertRow([line_geom, etid, unit, mn_etid]) 
printit("Done creating mapview stratlines.")
printit("Now creating mapview file with only surficial stratlines.")

#define mapview surficial stratlines output name with the same date number
mapview_surficial_stratlines = os.path.join(out_gdb, "mapview_surficial_stratlines_" + datestring + "_" + str(version))
printit("Mapview surficial stratline file will be {0}".format(mapview_surficial_stratlines))

#%%
# 7 set up unit list
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
# 8 Create geometry and export mapview surficial stratlines

# #make copy of stratlines_mapview and call it "stratlines_mapview_working"
stratlines_mapview_working = os.path.join(scratch_gdb, "stratlines_mapview_working")
arcpy.env.overwriteOutput = True
arcpy.conversion.ExportFeatures(stratlines_mapview, stratlines_mapview_working)

printit("Converting surficial stratlines to mapview.")
#loop thru unitlist from top to bottom. 
for unit in unitlist:
    printit("Working on {0}".format(unit))
    
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
# 9 Prep for intersect if checking sgpg match
printit("Finished creating mapview surficial stratlines.")

if check_sgpg_match:
    stratline_sgpg_mismatch_mapview_lines = os.path.join(out_gdb, "stratline_sgpg_mismatch_mapview_lines" + "_" + datestring + "_" + str(version))
    printit("Mismatch line and polygon files will end with {0}".format(datestring + "_" + str(version)))
    # 8 Prep for intersect
    #once mapview stratlines are intersected with sgpg, we will need to know which MapUnit field
    #comes from the stratlines and which comes from the sgpg

    # create temp copy of sgpg to add MapUnit_sgpg field name to clarify that it's for the sgpg
    printit("Exporting temp copy of surficial polygons to scratch gdb.")
    sgpg_temp = os.path.join(scratch_gdb, "sgpg_temp")
    arcpy.conversion.ExportFeatures(sgpg, sgpg_temp)

    #add fields and calculate them to equal MapUnit
    printit("Adding MapUnit_strat and MapUnit_sgpg fields.")
    expression = "!MapUnit!"
    arcpy.management.CalculateField(sgpg_temp, "MapUnit_sgpg", expression, '', '', 'TEXT')
    arcpy.management.CalculateField(mapview_surficial_stratlines, "MapUnit_strat", expression, '', '', 'TEXT')

    #delete MapUnit field from temp sgpg
    printit("Deleting MapUnit field from temp sgpg.")
    arcpy.management.DeleteField(sgpg_temp, "MapUnit")

#%%
# 10 Intersect and export output line and poly files
if check_sgpg_match:
    # 9 Intersect mapview stratlines with sgpg
    #then, we can see where the MapUnit_sgpg and MapUnit_strat fields are mismatched
    intersect_temp = os.path.join(scratch_gdb, "intersect_temp")
    arcpy.analysis.Intersect([mapview_surficial_stratlines, sgpg_temp], intersect_temp, '', '', 'LINE')

    #export final mapview lines
    #only export lines where MapUnit_strat =/= MapUnit_sgpg AND line segment is longer than 10 meters
    printit("Exporting mapview mismatch lines where MapUnit_strat is not equal to MapUnit_sgpg AND line segment is longer than 10 meters.")
    where_clause = "{0} <> {1} And {2} > 10".format("MapUnit_sgpg", "MapUnit_strat", "Shape_Length")
    arcpy.conversion.ExportFeatures(intersect_temp, stratline_sgpg_mismatch_mapview_lines, where_clause)

    # 10 Buffer lines to make it easier to see in mapview
    printit("Buffering mismatch lines to make them easier to see in mapview.")
    stratline_sgpg_mismatch_mapview_polys = os.path.join(out_gdb, "stratline_sgpg_mismatch_mapview_polys" + "_" +  datestring + "_" + str(version))
    arcpy.analysis.Buffer(stratline_sgpg_mismatch_mapview_lines, stratline_sgpg_mismatch_mapview_polys, 10, '', 'FLAT')

#%% 
# 11 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))