#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Generate Label points
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: May 2026
'''
This tool will automatically create label points for
labeling stratigraphy polygons. It will create a point
a short distance above the midpoint of each stratline,
labeled with the same unit label as the stratline.
These points can then be used to label polygons.
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
    stratlines = arcpy.GetParameterAsText(0)
    output_fc = arcpy.GetParameterAsText(1)
    temp_gdb = arcpy.GetParameterAsText(2)
    add_spatial_join = arcpy.GetParameter(3)
    ref_poly = arcpy.GetParameterAsText(4)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    stratlines = r'D:\Faribault_Local\temp_051326.gdb\stratlines_plate4_051326_adjusted'
    output_fc = r'D:\Faribault_Local\temp_051326.gdb\label_pt_test2'
    temp_gdb = r'D:\Faribault_Local\temp_051326.gdb'
    add_spatial_join = True # boolean, if Stacked and want to join mn_et_id and et_id
    ref_poly = r'D:\Faribault_Local\temp_051326.gdb\ref_poly' #appears if above is true
    printit("Variables set with hard-coded parameters for testing.")

#%% 
# 3 Set spatial reference
spatialref = arcpy.Describe(stratlines).spatialReference
if spatialref.name == "Unknown":
    printit("!!ERROR!!: {0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(stratlines)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(stratlines)))


#%%
# 4 check that mapunit field exists
unit_field = "MapUnit"
FieldExists(stratlines, unit_field)

#%%
# 5 dissolve by unit (no multipart) to make sure each line is only one segment
printit("Dissolving stratlines by unit and creating temporary working file.")
arcpy.env.overwriteOutput = True
stratlines_temp = os.path.join(temp_gdb, "stratlines_temp")
arcpy.management.Dissolve(stratlines, stratlines_temp, unit_field, '', 'SINGLE_PART')

#%%
# 6 create label x and y fields in temp stratline file
printit("Calculating xy point locations and adding attributes to temp line file.")
arcpy.management.AddFields(stratlines_temp, [["label_x", 'DOUBLE'], ["label_y", 'DOUBLE']])

#loop through each line and calculate middle vertex xy attributes
with arcpy.da.UpdateCursor(stratlines_temp, ["SHAPE@", "label_x", "label_y"]) as cursor:
    for line in cursor:
        #make a list of all the vertices in the line
        pointlist = []
        for vertex in line[0].getPart(0):
            point = arcpy.Point(vertex.X, vertex.Y)
            pointlist.append(point)
        #find the median midpoint
        vertex_num = len(pointlist)
        mid_index = int(vertex_num/2)
        midpoint = pointlist[mid_index]
        #the label point xy coordinates will be one meter above the midpoint of the line
        label_x = midpoint.X
        label_y = midpoint.Y + 1
        #append xy coordinates to attributes
        line[1] = label_x
        line[2] = label_y
        cursor.updateRow(line)

#%%
# 7 create point file based on label point attributes
printit("Creating point file based on calculated xy locations.")
#make table view of xy attributes
label_table_view = "label_table_view"
arcpy.env.overwriteOutput = True

#only create points for lines that have MapUnit attributes. check the length of the mapunit field.
where_clause = "CHAR_LENGTH({0}) > 1".format(unit_field)
arcpy.management.MakeTableView(stratlines_temp, label_table_view, where_clause)
#create output point file
arcpy.management.XYTableToPoint(label_table_view, output_fc, 'label_x', 'label_y', '', spatialref)

#%%
# 8 add spatial join mn_et_id and et_id
if add_spatial_join == True:
    printit("Executing spatial join with {0}".format(ref_poly))
    arcpy.management.AddSpatialJoin(output_fc, ref_poly, '', 'KEEP_ALL','', 'INTERSECT', '', '', 'PERMANENT_FIELDS')

#%%
# 9 Delete temp file
try: arcpy.management.Delete(stratlines_temp)
except: printit("Unable to delete {0}.".format(stratlines_temp))

#%% 
# 10 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))