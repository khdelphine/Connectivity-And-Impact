# ***************************************
# ***Overview***
# Script name: symbolization.py
# Purpose: This Arcpy script creates a raster with community impact score values,
#          based on over 10 criteria of economic and social vulnerability.
# Project: Connectivity and community impact analysis in Arcpy for potential bicycle infrastructure improvements.
# Extent: 4 PA Counties in Philadelphia suburbs.
# Last updated: April, 2019
# Author: Delphine Khanna
# Organization: Bicycle Coalition of Greater Philadelphia
# Note: This Arcpy script is meant to run in ArcGIS Desktop. It is NOT optimized for complete unsupervised automation.
# Note2: The prep steps for the 10 datasets is too idiosyncratic to each dataset to
#        to implement any common functions. So I just process them one after the other.
# Command: execfile(r'C:\Users\delph\Desktop\Github_repos\Connectivity-And-Impact\symbolization.py')
# ***************************************

import arcpy
import arcpy.sa
import arcpy.da
import datetime

# *********
# Set up global variables:
gdb_name = "\\script_output_CII2.gdb"
base_path = "C:\\Users\\delph\\Desktop\\GIS\\BCGP\\Connectivity_and_impact"
data_path = base_path + "\\Data"
orig_datasets_path = data_path + "\\Orig_datasets"
gdb_output = data_path + gdb_name
extent_4_counties = "Geography\\Boundaries_4_PA_counties_dissolved"
CII_score_overall = "Overall_Scores\\Impact_Score_Overall"

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
    arcpy.env.mask = current_extent


def apply_symbolization():
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    lyrFile = arcpy.mapping.Layer(base_path + "\\Lyr\\cii_overall_score_ras1d.lyr")

    rasters_to_symbolize = ["transportation_score_ras1", "cii_overall_score_ras1",
                            "health_score_ras1", "transportation_score_ras1",
                            "density_score_ras1", "ipd_score_ras1",
                            "pop_density_score_ras1", "employment_score_ras1",
                            "circuit_trails_score_ras1", "no_vehicle_score_ras1",
                            "rail_score_ras1", "trolley_score_ras1",
                            "bus_score_ras1", "obesity_score_ras1",
                            "nata_resp_score_ras1"]
    rasters_to_symbolize2 = ["density_score_ras1"]
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        if lyr.name in rasters_to_symbolize:
            arcpy.mapping.UpdateLayer(df, lyr, lyrFile, True)
            lyr.symbology.reclassify()
    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()

# ***************************************
# Begin Main
print_time_stamp("Start")
set_up_env()
apply_symbolization()
print_time_stamp("Done")
