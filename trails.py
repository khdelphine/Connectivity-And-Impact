
# ***************************************
# ***Overview***
# Script name: trails.py
# Purpose: This Arcpy script identifies the non-circuit trails with the highest connectivity and community impact score.
# Project: Connectivity and community impact analysis in Arcpy for potential bicycle infrastructure improvements.
# Extent: 4 PA Counties in Philadelphia suburbs.
# Last updated: April, 2019
# Author: Delphine Khanna
# Organization: Bicycle Coalition of Greater Philadelphia
# Note: This Arcpy script is meant to run in ArcGIS Desktop. It is NOT optimized for complete unsupervised automation.
# Command: execfile(r'C:\Users\delph\Desktop\Github_repos\Connectivity-And-Impact\trails.py')
# ***************************************

import arcpy
import arcpy.sa
import arcpy.da
import datetime

# *********
# Set up global variables:
gdb_name = "\\ScriptOutput2.gdb"
base_path = "C:\\Users\\delph\\Desktop\\GIS\\BCGP\\Connectivity_and_impact"
data_path = base_path + "\\Data"
gdb_output = data_path + gdb_name
extent_4_counties = "Geography\\Boundaries_4_PA_counties_dissolved"
#lts3_lines = gdb_output + "\\LTS3_top20_connectivity"
CII_score_overall = "Overall_Scores\\Impact_Score_Overall"
islands_orig = "Islands\\DVRPC_Bike_Stress_LTS_1__2_Islands"
#islands = "Islands\\LTS1_2_islands_dissolved_gte_1000m_no0Strong_4counties_SAMPLE"
islands = gdb_output + "\\islands"
buffered_islands = gdb_output + "\\buffered_islands"
islands_with_CII_scores_table = gdb_output + "\\islandsWithCIIScores_table"
islands_with_score =  gdb_output + "\\islands_with_score"
trails = "Non-Circuit_Trails\\Trails_Non_Circuit_Proj_4counties"
trails_intersecting = gdb_output + "\\trails_intersecting"
trails_intersecting_gte_2 = gdb_output + "\\trails_intersecting_gte_2"

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

# Prepare the LTS1-2 Islands layer:
def prep_islands():
    # Define the local variables:
    islands_proj = gdb_output + "\\islands_proj"
    islands_dissolved = gdb_output + "\\islands_dissolved"
    islands_gt_0 = gdb_output + "\\islands_gt_0"
    islands_gte_1000m = gdb_output + "\\islands_gte_1000m"

    # Reproject the original Islands layer:
    target_spatial_reference = arcpy.SpatialReference('NAD 1983 UTM Zone 18N')
    arcpy.Project_management(islands_orig, islands_proj, target_spatial_reference, "WGS_1984_(ITRF00)_To_NAD_1983")
    # Dissolve the layer on the STRONG field -- there is now only 1 polyline per island:
    arcpy.Dissolve_management(islands_proj, islands_dissolved, "STRONG")

    # Remove the islands where STRONG is 0, as 0 stands in for a catch all category:
    arcpy.SelectLayerByAttribute_management("islands_dissolved", "NEW_SELECTION", "STRONG > 0")
    # Save to a new feature class and do some clean up:
    arcpy.CopyFeatures_management("islands_dissolved", islands_gt_0)
    arcpy.SelectLayerByAttribute_management("islands_dissolved", "CLEAR_SELECTION")

    # Keep only the islands greater than 1000 meters in length, as the really tiny islands do not seem worth our attention.
    arcpy.SelectLayerByAttribute_management("islands_gt_0", "NEW_SELECTION", "Shape_Length >= 1000")
    # Save to a new feature class and do some clean up:
    arcpy.CopyFeatures_management("islands_gt_0", islands_gte_1000m)
    arcpy.SelectLayerByAttribute_management("islands_gt_0", "CLEAR_SELECTION")

    # Select only the island polylines that intersects with 4 PA counties, with a spatial join:
    arcpy.SpatialJoin_analysis(islands_gte_1000m, extent_4_counties, islands,
                               "JOIN_ONE_TO_ONE", "KEEP_COMMON", match_option="INTERSECT")

    # Add new field "Orig_Length". We will use it later.
    arcpy.AddField_management(islands, "Orig_Length", "DOUBLE")
    arcpy.CalculateField_management(islands, "Orig_Length", "!Shape_Length!", "PYTHON_9.3")

    # Create a 100 meter buffer arounds the islands
    arcpy.Buffer_analysis(islands, buffered_islands, "100 Meters", "FULL", "ROUND")


def compute_CII_per_island():
    # Compute the CII score per island as zonal statistics:
    arcpy.CheckOutExtension("Spatial")
    arcpy.sa.ZonalStatisticsAsTable(buffered_islands, "STRONG", CII_Score_Overall,
                                    islands_with_CII_scores_table, "DATA", "MEAN")
    # Rename field MEAN to CII_Score_Overall
    arcpy.AlterField_management(islands_with_CII_scores_table, "MEAN", "CII_Score_Overall")
    # Join the resulting table back to the original islands feature class:
    arcpy.AddJoin_management(islands, "STRONG", islands_with_CII_scores_table, "STRONG", "KEEP_ALL")
    # Remove any island where the CII_Score_Overall is null:
    arcpy.SelectLayerByAttribute_management(islands, "NEW_SELECTION", "CII_Score_Overall IS NOT NULL")
    # Save to a new feature class and do some clean up:
    arcpy.CopyFeatures_management(islands, islands_with_score)
    arcpy.SelectLayerByAttribute_management(islands, "CLEAR_SELECTION")
    arcpy.RemoveJoin_management(islands)
    # Delete some unnecessary fields:
    drop_fields = ["IslandsWithCIIScores_table_OBJECTID","IslandsWithCIIScores_table_STRONG",
                  "IslandsWithCIIScores_table_COUNT", "IslandsWithCIIScores_table_AREA"]
    arcpy.DeleteField_management(islands_with_score, drop_fields)
    # Rename some fields to their alias, to get rid of exagerated long names:
    field_list = arcpy.ListFields(islands_with_score)
    for field in field_list:
        if field.aliasName in ["STRONG", "Orig_length", "CII_Score_Overall"]:
            arcpy.AlterField_management(islands_with_score, field.name, field.aliasName)

# Prepare the Non-Circuit Trails layer:
def prep_trails():
    # Add new field "Trail_ID" and copy the OID in it for clarity:
    arcpy.AddField_management(trails, "Trail_ID", "LONG")
    arcpy.CalculateField_management(trails, "Trail_ID", "!OID!", "PYTHON_9.3")
    # Delete some unnecessary fields:
    dropFields = ["FolderPath","SymbolID", "AltMode", "Base", "Clamped", "Extruded", "Snippet", "PopupInfo"]
    arcpy.DeleteField_management(trails, dropFields)

# Set the merge rules in the fieldMappings for a spatial join:
def set_up_merge_rules(field_name, merge_rule, field_mappings):
    # Get the field map index of this field and get the field map:
    field_index = field_mappings.findFieldMapIndex(field_name)
    field_map = field_mappings.getFieldMap(field_index)
    # Update the field map with the new merge rule (by default the merge rule is "First"):
    field_map.mergeRule = merge_rule
    # Replace with the updated field map:
    field_mappings.replaceFieldMap(field_index, field_map)

# For each trail, find all intersecting islands:
def find_trail_island_intersections():
    # Create the field mapping object that will be used in the spatial join:
    field_mappings = arcpy.FieldMappings()
    # Populate the field mapping object with the fields from both feature classes of interest
    field_mappings.addTable(trails)
    field_mappings.addTable(islands_with_score)
    #Set up merge rules:
    # Orig_length -- we will sum up the length of all intersecting islands for each trail:
    set_up_merge_rules("Orig_length","Sum", field_mappings)
    # STRONG (i.e., island ID) -- we will count the number of all intersecting islands for each trail:
    set_up_merge_rules("STRONG", "Count", field_mappings)
    # CII_Score_Overall -- we will compute the CII score average among all intersecting islands for each trail:
    set_up_merge_rules("CII_Score_Overall", "Mean", field_mappings)

    # Do the spatial join to find all the islands that intersect with each trail:
    arcpy.SpatialJoin_analysis(trails, islands_with_score, trails_intersecting,
                               "JOIN_ONE_TO_ONE", "KEEP_ALL", field_mappings, "INTERSECT", search_radius="50 Meters")
    # Rename fields:
    arcpy.AlterField_management(trails_intersecting, "Orig_length", "Length_of_All_Islands", "Length_of_All_Islands")
    arcpy.AlterField_management(trails_intersecting, "STRONG", "Num_of_Islands", "Num_of_Islands")
    arcpy.AlterField_management(trails_intersecting, "CII_Score_Overall", "Trail_CII_Score", "Trail_CII_Score")
    # Delete an unnecessary field:
    drop_fields = ["TARGET_FID"]
    arcpy.DeleteField_management(trails_intersecting, drop_fields)

# Keep only the trails that intersect with 2 islands or more:
def filter_2_or_more_islands():
    #Select by Attribute trails that intersect with 2 islands or more:
    ### Later on >=2
    arcpy.SelectLayerByAttribute_management("trails_intersecting", "NEW_SELECTION", "Num_of_Islands >=1")
    # Save to a new feature class and do some clean up:
    arcpy.CopyFeatures_management("trails_intersecting", trails_intersecting_gte_2)
    arcpy.SelectLayerByAttribute_management("trails_intersecting", "CLEAR_SELECTION")

# Get the maximum value for a feature class attribute across all rows:
def get_max(feat_class, attribute):
    max_value = 0
    with arcpy.da.SearchCursor(feat_class, attribute) as cursor:
        for row in cursor:
             max_value = max(cursor)
    return max_value[0]

# Compute the final score for each Non-Circuit Trail:
def compute_trail_scores():
    # Add new field "Total_connectivity_score" where we will compute the
    # total connectivity score for each trail:
    arcpy.AddField_management(trails_intersecting_gte_2, "Total_connectivity_score", "DOUBLE")

    length_of_all_islands_max = get_max("trails_intersecting","Length_of_All_Islands")
    num_of_islands_max = get_max("trails_intersecting","Num_of_Islands")
    trail_CII_score_max = get_max("trails_intersecting","Trail_CII_Score")
    #print(length_of_all_islands_max)
    #print(num_of_islands_max)
    #print(trail_CII_score_max)
    expr = ("(((!Length_of_all_Islands! /" + str(length_of_all_islands_max) +
            " + !Num_of_Islands! / " + str(num_of_islands_max) +
            " + !Trail_CII_Score!/" + str(trail_CII_score_max) +
            ")/3)*100)")
    #print(expr)
    arcpy.CalculateField_management(trails_intersecting_gte_2, "Total_connectivity_score",
                                    expr, "PYTHON_9.3")

# ***************************************
# Begin Main
print_time_stamp("Start")
set_up_env()
#prep_gdb()
prep_islands2()
#compute_CII_per_island()
#prep_trails()
#find_trail_island_intersections()
#filter_2_or_more_islands()
#compute_trail_scores()
print_time_stamp("Done")
