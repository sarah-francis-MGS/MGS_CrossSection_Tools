#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Convert Stratlines to Map View
# Coded by Sarah Francis, Minnesota Geological Survey
# Created Date: July 2022, Updated March 2026
'''
This script converts cross section stratigraphy lines to map view. Lines will
retain all vertices, cross section id numbers, and unit information. Map view 
lines are then used to create unit masks or to check surficial geology/stratline
match.
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
    output_location = arcpy.GetParameterAsText(2)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln_file = r'D:\FaribaultSandModel\Run2_022326\SandModeling_TIN.gdb\xsln'
    strat_all_orig = r'D:\FaribaultSandModel\Run2_022326\SandModeling_TIN.gdb\all_strat_vertices'
    output_location = r'D:\Faribault_Local\script_testing_030526.gdb' #gdb
    printit("Variables set with hard-coded parameters for testing.")

#%%
# 3 Define additional parameters and check that they exist

#xsln_file = os.path.join(sandmodel_gdb, "xsln") # map view
xsln_etid_field = 'et_id'
#strat_all_orig = os.path.join(sandmodel_gdb, "all_strat_vertices") # stratlines drawn by geologist merged into one file with et_id and unit attributes
stratline_etid_field = 'et_id'
stratline_unit_field = 'MapUnit'
#output_location = sandmodel_gdb

#FileExists(xsln_file)
#FileExists(strat_all_orig)
FieldExists(xsln_file, xsln_etid_field)
FieldExists(xsln_file, 'mn_et_id')
FieldExists(strat_all_orig, stratline_etid_field)
FieldExists(strat_all_orig, 'mn_et_id')
FieldExists(strat_all_orig, stratline_unit_field)

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

month = toolstart.strftime("%m")
year = toolstart.strftime("%y")
day = toolstart.strftime("%d")
version = 1
datestring = month+day+year

out_fc_name = "stratlines_mapview_" + datestring + "_" + str(version)
out_fc = os.path.join(output_location, out_fc_name)

while arcpy.Exists(out_fc):
    version = version + 1
    out_fc_name = "stratlines_mapview_" + datestring + "_" + str(version)
    out_fc = os.path.join(output_location, out_fc_name)

printit("Creating empty output file {0}.".format(out_fc))
arcpy.management.CreateFeatureclass(output_location, out_fc_name, 'POLYLINE', '', '', '', spatialref)

output_fields = [[stratline_etid_field, 'TEXT'], [stratline_unit_field, 'TEXT'], ["mn_et_id", "TEXT"]]

arcpy.management.AddFields(out_fc, output_fields)

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
                with arcpy.da.InsertCursor(out_fc, ['SHAPE@', stratline_etid_field, stratline_unit_field, 'mn_et_id']) as out_cursor:
                    out_cursor.insertRow([line_geom, etid, unit, mn_etid]) 

#%% 
# 7 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))