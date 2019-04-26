
# ***************************************
# ***Overview***
# Script name: roads.py
# Purpose: This Arcpy script identifies the LTS3 road segments with the highest connectivity and community impact score.
# Project: Connectivity and community impact analysis in Arcpy for potential bicycle infrastructure improvements.
# Extent: 4 PA Counties in Philadelphia suburbs.
# Last updated: April, 2019
# Author: Delphine Khanna
# Organization: Bicycle Coalition of Greater Philadelphia
# Note: This Arcpy script is meant to run in ArcGIS Desktop. It is NOT optimized for complete unsupervised automation.
# Command: execfile(r'C:\Users\delph\Desktop\Github_repos\Connectivity-And-Impact\roads.py')
# ***************************************

import arcpy
import arcpy.sa
import arcpy.da
import datetime

# *********
# Option switch:
REMOVE_INTERMEDIARY_LAYERS_OPTION = "yes" # or "no"

# *********
# Set up global variables:
gdb_name = "\\script_output_roads.gdb"
base_path = "C:\\Users\\delph\\Desktop\\GIS\\BCGP\\Connectivity_and_impact"
data_path = base_path + "\\Data"
gdb_output = data_path + gdb_name
extent_4_counties = "Geography\\Boundaries_4_PA_counties_dissolved"
CII_score_overall = "Overall_Scores\\Impact_Score_Overall"
lts3_orig = "LTS3_roads\\DVRPC_Bike_Stress_Suburban_LTS_3_Connections"
lts3_top30pct = gdb_output + "\\lts3_top30pct"
lts3_top30pct_buffered = gdb_output + "\\lts3_top30pct_buffered"
lts3_top30pct_with_CII_scores = gdb_output + "\\lts3_top30pct_with_CII_scores"

# *****************************************
# Functions

# Print the current action and time:
def print_time_stamp(action):
    current_DT = datetime.datetime.now()
    print(action + " Processing -- "
          + current_DT.strftime("%Y-%b-%d %I:%M:%S %p"))

# Set up the ArcGIS environment variables:
def set_up_env():
    arcpy.env.workspace = gdb_output
    arcpy.env.overwriteOutput = True
    current_extent = extent_4_counties
    arcpy.env.extent = current_extent
    arcpy.env.outputCoordinateSystem = current_extent

# Create a new geodatabase and to put all the output for this batch:
def prep_gdb():
    arcpy.Delete_management(gdb_output)
    arcpy.CreateFileGDB_management(data_path, gdb_name)

# Optionally remove intermediary layers generated during the analysis:
def remove_intermediary_layers(layers_to_remove):
    if REMOVE_INTERMEDIARY_LAYERS_OPTION == "yes":
        mxd=arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            if lyr.name in layers_to_remove:
                arcpy.mapping.RemoveLayer(df, lyr)

# Select the top 30% LTS3 road segments:
def select_top30pct_lts3():
    # Select the top 30% LTS3 road segments using the attribute Top30percent:
    arcpy.SelectLayerByAttribute_management(lts3_orig, "NEW_SELECTION", "Top30perce = 1")
    # Save to a new feature class and do some clean up:
    arcpy.CopyFeatures_management(lts3_orig, lts3_top30pct)
    arcpy.SelectLayerByAttribute_management(lts3_orig, "CLEAR_SELECTION")

# Create a 1 mile meter buffer arounds every LTS3 road segment:
def buffer_lts3():
    arcpy.Buffer_analysis(lts3_top30pct, lts3_top30pct_buffered, "1609.34 Meters", "FULL", "ROUND")

# Compute CII scores per LTS3 road segment
def compute_CII_scores_per_lts3_NOT():
    # Define local variables
    lts3_unprocessed = gdb_output + "\\lts3_unprocessed"
    lts3_temp = gdb_output + "\\lts3_temp"
    lts3_with_CII_scores_table = gdb_output + "\\lts3_with_CII_scores_table"
    new_lts3_unprocessed = gdb_output + "\\new_lts3_unprocessed"

    # Prepare everything before the loop:
    arcpy.CheckOutExtension("Spatial")
    arcpy.Delete_management(lts3_unprocessed)
    arcpy.CopyFeatures_management("lts3_top30pct_buffered", lts3_unprocessed)
    # Rename the EDGE field to its simplest form:
    field_list = arcpy.ListFields(lts3_unprocessed)
    for field in field_list:
        if field.aliasName == "EDGE":
            arcpy.AlterField_management(lts3_unprocessed, field.name, "EDGE")
            break

    # Initialize the number_of_rows variable and the "i" iteration counter:
    num_of_rows = int(arcpy.GetCount_management(lts3_unprocessed)[0])
    i = 1

    # Loop to perform the Zonal Statistics as Table iteratively, processing each time them
    # subset of rows that were not already processed in the last iteration
    while num_of_rows > 0:
        # At each iteration we will generate a new lts3_with_CII_scores_table:
        lts3_with_CII_scores_table  = gdb_output + "\\lts3_with_CII_scores_table" + str(i)
        # Compute the CII score per LTS3 segment as zonal statistics. The output is a table:
        arcpy.sa.ZonalStatisticsAsTable(lts3_unprocessed, "EDGE", CII_score_overall,
                                        lts3_with_CII_scores_table, "DATA", "MEAN")

        # Create a temporary feature class that contains the results of the Zonal Statistics tool
        lts3_table = "lts3_with_CII_scores_table"  + str(i)
        arcpy.AddJoin_management("lts3_unprocessed", "EDGE", lts3_table, "EDGE", "KEEP_ALL")
        arcpy.CopyFeatures_management("lts3_unprocessed", lts3_temp)
        # Remove the join and delete lts3_unprocessed:
        arcpy.RemoveJoin_management("lts3_unprocessed") #Not needed?
        arcpy.Delete_management(lts3_unprocessed)

        # Put any LTS3 segment that didn't not get processed in a new feature class
        # lts3_unprocessed. They can be recognized because some of their attributes are NULL.
        expr = "lts3_with_CII_scores_table" + str(i) + "_MEAN IS NULL"
        print(expr)
        arcpy.SelectLayerByAttribute_management("lts3_temp", "NEW_SELECTION", expr)
        arcpy.CopyFeatures_management("lts3_temp", lts3_unprocessed)
        arcpy.SelectLayerByAttribute_management("lts3_temp", "CLEAR_SELECTION")

        # Delete all fields in new_lts3_unprocessed that came from lts3_with_CII_scores_table, so that
        # we start with a blank slate in the next round
        drop_fields = ["lts3_with_CII_scores_table" + str(i) + "_OBJECTID",
                       "lts3_with_CII_scores_table" + str(i) + "_EDGE",
                       "lts3_with_CII_scores_table" + str(i) + "_COUNT",
                       "lts3_with_CII_scores_table" + str(i) + "_AREA",
                       "lts3_with_CII_scores_table" + str(i) + "_MEAN"]
        arcpy.DeleteField_management(lts3_unprocessed, drop_fields)

        # Rename the EDGE field to its simplest form in lts3_unprocessed
        field_list = arcpy.ListFields(lts3_unprocessed)
        for field in field_list:
            if field.aliasName == "EDGE":
                print(field.name)
                arcpy.AlterField_management(lts3_unprocessed, field.name, "EDGE")
                break

        # Increment the counters
        num_of_rows = int(arcpy.GetCount_management("lts3_unprocessed")[0])
        i += 1
        print("num_of_rows: " + str(num_of_rows))
        print("i: "+ str(i))


def select_top_third():
    1


# ***************************************
# Begin Main
print_time_stamp("Start")
set_up_env()
#prep_gdb()
#select_top30pct_lts3()
#buffer_lts3()
compute_CII_scores_per_lts3()
print_time_stamp("Done")
