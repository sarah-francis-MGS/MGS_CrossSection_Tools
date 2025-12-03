#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Get QDI Data
# Created by Bill Grimm, Minnesota Geological Survey
# Modified from GetCWIdata.py by Sarah Francis, Minnesota Geological Survey
# Created Date: November-December 2024, November 2025
'''
This script gets QDI data for a buffered cross section line file
and creates a well point file and strat point file.
'''

# %%
# 1 Import modules and define functions

import arcpy
import os
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement functions for testing and compiled geoprocessing tool

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
        printerror("Error. {0} field does not exist in {1}.".format(field_name, os.path.basename(dataset)))
        
# Define function to check for geometry type

def correctGeometry(file, geometry1, geometry2):
    desc = arcpy.Describe(file)
    if not desc.shapeType == geometry1:
        if not desc.shapeType == geometry2:
            printerror("Error: {0} does not have {1} geometry.".format(os.path.basename(file), geometry1))
    #else: printit("{0} has {1} geometry.".format(os.path.basename(file), geometry))

# %%
# 2 Set parameters to work in testing and compiled geoprocessing tool

# !!!!!!!!!!!!!!!!!!!!!!
#change the variable below if running in an IDE.
# MAKE SURE TO CHANGE BACK TO "PRO" WHEN FINISHED
#-----------------------------------------------------------------
# run_location = "ide"
run_location = "Pro"
#-----------------------------------------------------------------
#!!!!!!!!!!!!!!!!!!!!!!!

if run_location == "Pro":
    #variable = arcpy.GetParameterAsText(0)
    output_gdb = arcpy.GetParameterAsText(0)
    xsln = arcpy.GetParameterAsText(1)
    buffer_distance = int(arcpy.GetParameterAsText(2)) #meters
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    output_gdb = r'H:\Scripts\Testing\GetQDItesting_OtterTail.gdb'
    xsln = r'H:\Scripts\Testing\GetQDItesting_OtterTail.gdb\cross_section_lines'
    buffer_distance = 500 #meters, half of xsln spacing
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 Buffer xsln file
arcpy.env.overwriteOutput = True
printit("Buffering xsln file.")

xsln_buffer = os.path.join(output_gdb, "xsln_buffer")
arcpy.analysis.Buffer(xsln, xsln_buffer, buffer_distance, '', "FLAT")

#%% 4 Clip statewide QDI location file by xsln buffer
printit("Clipping statewide QDI location file with xsln buffer.")
arcpy.env.overwriteOutput = True

state_qdi_loc = r'L:\gis_umnad\sdeConnections\mgs_qdi\DB4E_mgs_qdi_mgsstaff.sde\mgs_qdi.qdi.qdix'
qdi_loc_temp = os.path.join(output_gdb, 'qdi_loc_temp')

arcpy.analysis.Clip(state_qdi_loc, xsln_buffer, qdi_loc_temp)

#%%
# 5 Join attributes from xsln to qdi_loc
printit("Spatially joining xsln attributes to well location points.")
arcpy.env.overwriteOutput = True
qdi_loc = os.path.join(output_gdb, 'qdi_loc')
arcpy.analysis.SpatialJoin(qdi_loc_temp, xsln_buffer, qdi_loc, 'JOIN_ONE_TO_MANY')

'''
printit("Creating archival qdi_loc file with today's date.")
#create copy of qdi_loc file with date for archival purposes
now = datetime.datetime.now()
month = now.strftime("%m")
day = now.strftime("%d")
year = now.strftime("%y")
date = str(month + day + year)

arcpy.conversion.FeatureClassToFeatureClass(qdi_loc, output_gdb, "qdi_loc" + date)
'''

#%%
# 6 Make strat table
printit("Clipping statewide stratigraphy data with xsln buffer.")
state_qdi_strat = r'L:\gis_umnad\sdeConnections\mgs_qdi\DB4E_mgs_qdi_mgsstaff.sde\mgs_qdi.qdi.vw_qdst'

# Clip statewide strat points
qdi_strat_temp = os.path.join(output_gdb, "qdi_strat_temp")
arcpy.analysis.Clip(state_qdi_strat, xsln_buffer, qdi_strat_temp)

# Spatially join with xsln buffer
printit("Spatially joining xsln attributes to stratigraphy points.")
qdi_strat_temp2 = os.path.join(output_gdb, "qdi_strat_temp2")
arcpy.analysis.SpatialJoin(qdi_strat_temp, xsln_buffer, qdi_strat_temp2, 'JOIN_ONE_TO_MANY')

# Export strat points temp2 to geodatabase table
printit("Exporting temp stratigraphy points to geodatabase table.")
temp_table_view = "temp_table_view"
arcpy.management.MakeTableView(qdi_strat_temp2, temp_table_view)
strat_table = os.path.join(output_gdb, "strat_qdi")
try:
    # Table To Table is apparently deprecated, but the newer version (ExportTable) isn't working?
    # This way, one of them should work.
    arcpy.conversion.ExportTable(temp_table_view, strat_table)
except:
    arcpy.conversion.TableToTable(temp_table_view, output_gdb, "strat_qdi")
    
#%%
# 7 Delete temporary files
printit("Deleting temporary files.")
try:
    arcpy.management.Delete(qdi_loc_temp)
except:
    printit("Unable to delete {0}.".format(qdi_loc_temp))
    
try:
    arcpy.management.Delete(qdi_strat_temp)
except:
    printit("Unable to delete {0}.".format(qdi_strat_temp))
    
try:
    arcpy.management.Delete(qdi_strat_temp2)
except:
    printit("Unable to delete {0}.".format(qdi_strat_temp2))

#%%
# 8 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit("Tool completed at {0}. Elapsed time: {1}. You're a wizard, Harry!".format(toolend, toolelapsed))
#%%
    





        


