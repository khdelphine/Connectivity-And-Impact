
# ***************************************
# ***Overview***
# Script name: utilities.py
# Purpose: This Python module defines a few functions that are used in all the other
# scripts of the project.
# Project: Connectivity and community impact analysis in Arcpy for potential bicycle infrastructure improvements.
# Extent: 4 PA Counties in Philadelphia suburbs.
# Last updated: May 9, 2019
# Author: Delphine Khanna
# Organization: Bicycle Coalition of Greater Philadelphia
# ***************************************

import arcpy
import datetime

# *****************************************
# Functions

# Print the current action and time
def print_time_stamp(action):
    current_DT = datetime.datetime.now()
    print(action + " Processing -- "
          + current_DT.strftime("%Y-%b-%d %I:%M:%S %p"))

# Load ancillary layers like the 4 counties' boundaries:
def load_ancillary_layers():
    arcpy.MakeFeatureLayer_management(common_util_path + "\\extent_4_counties", "extent_4_counties")
    arcpy.MakeFeatureLayer_management(common_util_path + "\\boundaries_4_PA_counties", "boundaries_4_PA_counties")
    arcpy.MakeFeatureLayer_management(common_util_path + "\\municipalities_4_PA_counties", "municipalities_4_PA_counties")
    arcpy.MakeFeatureLayer_management(common_util_path + "\\major_cities_4_PA_counties", "major_cities_4_PA_counties")

# Set up the ArcGIS environment variables
def set_up_env():
    arcpy.env.workspace = gdb_output
    arcpy.env.overwriteOutput = True
    current_extent = "extent_4_counties"
    arcpy.env.extent = current_extent
    arcpy.env.outputCoordinateSystem = current_extent
    arcpy.env.mask = current_extent
    arcpy.env.snapraster = current_extent
    arcpy.env.outputCoordinateSystem = current_extent
    arcpy.env.cellSize = 30

# Create a new geodatabase and to put all the output for this batch
def prep_gdb():
    if arcpy.Exists(gdb_output):
        arcpy.Delete_management(gdb_output)
    arcpy.CreateFileGDB_management(data_path, gdb_output_name)

# Optionally remove intermediary layers generated during the analysis
def remove_intermediary_layers(layers_to_remove):
    if REMOVE_INTERMEDIARY_LAYERS_OPTION == "yes":
        mxd=arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            if lyr.name in layers_to_remove:
                arcpy.mapping.RemoveLayer(df, lyr)
