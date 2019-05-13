# ***************************************
# ***Overview***
# Script name: symbolization.py
# Purpose: This Arcpy script applies chosen symbolizations to a list of vectors and rasters.
# Project: Connectivity and community impact analysis in Arcpy for potential bicycle infrastructure improvements.
# Extent: 4 PA Counties in Philadelphia suburbs.
# Last updated: May 12, 2019
# Author: Delphine Khanna
# Organization: Bicycle Coalition of Greater Philadelphia
# Note: This Arcpy script is meant to run in ArcGIS Desktop. It is NOT optimized for complete unsupervised automation.
# Commands for the ArcGIS Python interpreter, to (1) get into the right directory, and (2) execute this script
#   import os; os.chdir("C:\Users\delph\Desktop\Github_repos\Connectivity-And-Impact"); execfile(r'symbolization.py')
# ***************************************

# Import Arcpy modules:
import arcpy

# Import local modules:
from config import *
from utilities import *

# This is the list of all the CII-related vectors:
vectors_to_symbolize = ["major_cities_4_PA_counties",
                        "municipalities_4_PA_counties",
                        "boundaries_4_PA_counties",
                        "extent_4_counties",
                        "counties_except_delaware"]

# This is the list of all the CII-related rasters:
rasters_to_symbolize1 = ["nata_resp_score_ras", "obesity_score_ras",
                        "bus_score_ras", "trolley_score_ras",
                        "rail_score_ras", "no_vehicle_score_ras",
                        "circuit_trails_score_ras", "employment_score_ras",
                        "pop_density_score_ras", "health_score_ras",
                        "transportation_score_ras", "density_score_ras",
                        "ipd_score_ras","cii_overall_score_ras"]

# When wanting to test one raster at a time
rasters_to_symbolize = ["cii_overall_score_ras1"]
# *****************************************
# Functions

# Apply the chosen symbolization to each vector layer
def symbolize_vectors():
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd)[0]

    # Loop through every layer in the mxd document
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        # Check if it is in the list of vector layers:
        if lyr.name in vectors_to_symbolize:
            # Get the chosen Lyr template used
            lyrFile = arcpy.mapping.Layer(base_path + "\\Lyr\\" + lyr.name + ".lyr")
            print("Symbolize:" + lyr.name)
            # Apply the Lyr template to it
            arcpy.mapping.UpdateLayer(df, lyr, lyrFile, True)
    # Refresh the display of the mxd
    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()

# Recalculate the statistics for every rasters -- This is necessary for the step
# lyr.symbology.reclassify() to work properly later on
def recalculate_raster_statistics():
    for ras in rasters_to_symbolize:
        # First some cleanup (we need to remove the previously displayed layer):
        remove_intermediary_layers([ras + "1"])

        # Now build the pyramids, and calculate the statistics on each rasters
        # on the drive. The Calculate_Statistics will also show the raster as a layer:
        print("Calculate Stats:" + ras)
        arcpy.BatchBuildPyramids_management(gdb_output + "\\" + ras)
        arcpy.CalculateStatistics_management(gdb_output + "\\" + ras)

# Apply the chosen symbolization to each raster
def apply_raster_symbolization():
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    # Get the chosen Lyr template used
    lyrFile = arcpy.mapping.Layer(base_path + "\\Lyr\\cii_overall_score_ras1e.lyr")

    # Loop through every layer in the mxd document
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        # Check if it is in the list of rasters
        if lyr.name in rasters_to_symbolize:
            print("Symbolize:" + lyr.name)
            # If so, apply the Lyr template to it
            arcpy.mapping.UpdateLayer(df, lyr, lyrFile, True)
            # And reclassify, so that the classification breaks are adapted #
            # the current raster
            lyr.symbology.reclassify()
            #print(lyr.symbology.classBreakValues)
    # Refresh the display of the mxd
    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()

def symbolize_rasters():
    #recalculate_raster_statistics()
    apply_raster_symbolization()

# ***************************************
# Main
print_time_stamp("Start")
symbolize_vectors()
symbolize_rasters()
print_time_stamp("Done")
