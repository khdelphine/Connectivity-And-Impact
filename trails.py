
# ***************************************
# ***Overview***
# Script name: trails.py
# Purpose: This Arcpy script identifies the non-circuit trails with the highest connectivity and community impact score.
# Project: Connectivity and community impact analysis in Arcpy for potential bicycle infrastructure improvements.
# Extent: 4 PA Counties in Philadelphia suburbs.
# Last updated: May 11, 2019
# Author: Delphine Khanna
# Organization: Bicycle Coalition of Greater Philadelphia
# Note: This Arcpy script is meant to run in ArcGIS Desktop. It is NOT optimized for complete unsupervised automation.
# Commands for the ArcGIS Python interpreter:
#    1. To get into the current directory: import os; os.chdir("C:\Users\delph\Desktop\Github_repos\Connectivity-And-Impact")
#    2. Execute this file: execfile(r'trails.py')
# ***************************************

# Import Arcpy modules:
import arcpy
import arcpy.sa # Spatial Analyst
import arcpy.da # Data Access

# Import local modules:
from config import *
from utilities import *


# *****************************************
# Functions

# Load the main datasets
def load_main_data():
    # Convert the non-circuit trails from kml
    arcpy.KMLToLayer_conversion (trails_orig, trails_converted_path, "trails_converted")
    # Reproject the converted non-circuit trails feature class
    target_spatial_reference = arcpy.SpatialReference('NAD 1983 UTM Zone 18N')
    arcpy.Project_management("trails_converted\\Polylines", "trails_proj", target_spatial_reference, "WGS_1984_(ITRF00)_To_NAD_1983")

    # Load the CII score raster
    arcpy.MakeRasterLayer_management(cii_overall_score_ras, "cii_overall_score_ras1")

    # Load the LTS1-2 Islands feature class, and reproject it
    arcpy.MakeFeatureLayer_management(islands_orig, "islands_orig")
    arcpy.Project_management("islands_orig", "islands_proj", target_spatial_reference, "WGS_1984_(ITRF00)_To_NAD_1983")

    # Remove intermediary layers
    remove_intermediary_layers(["trails_converted", "islands_orig"])

    # We have the option to load the XXX layer with the CII scores instead of regenerating it:
    if COMPUTE_ONLY_FINAL_SCORES_OPTION == "yes":
        arcpy.MakeFeatureLayer_management("islands", "islands")
        arcpy.MakeFeatureLayer_management("buffered_islands", "buffered_islands")
        arcpy.MakeFeatureLayer_management("islands_with_score", "islands_with_score")
        arcpy.MakeFeatureLayer_management("trails", "trails")
        arcpy.MakeFeatureLayer_management("trails_intersecting", "trails_intersecting")
        arcpy.MakeFeatureLayer_management("trails_intersecting_gte_2", "trails_intersecting_gte_2")


# Prepare the LTS1-2 Islands layer
def prep_islands():
    # Dissolve the layer on the STRONG field -- there is now only 1 polyline per island
    arcpy.Dissolve_management("islands_proj", "islands_dissolved", "STRONG")
    # Remove the islands where STRONG is 0, as 0 stands in for a catch all category
    arcpy.SelectLayerByAttribute_management("islands_dissolved", "NEW_SELECTION", "STRONG > 0")
    # Save to a new feature class and do some clean up
    arcpy.CopyFeatures_management("islands_dissolved", "islands_gt_0")
    arcpy.SelectLayerByAttribute_management("islands_dissolved", "CLEAR_SELECTION")
    # Keep only the islands greater than 1000 meters in length, as the really tiny islands do not seem worth our attention.
    arcpy.SelectLayerByAttribute_management("islands_gt_0", "NEW_SELECTION", "Shape_Length >= 1000")
    # Save to a new feature class and do some clean up
    arcpy.CopyFeatures_management("islands_gt_0", "islands_gte_1000m")
    arcpy.SelectLayerByAttribute_management("islands_gt_0", "CLEAR_SELECTION")

    # Select only the island polylines that intersects with 4 PA counties, with a spatial join
    arcpy.SpatialJoin_analysis("islands_gte_1000m", "extent_4_counties", "islands",
                               "JOIN_ONE_TO_ONE", "KEEP_COMMON", match_option="INTERSECT")

    # Add new field "Orig_Length". We will use it later.
    arcpy.AddField_management("islands", "Orig_Length", "DOUBLE")
    arcpy.CalculateField_management("islands", "Orig_Length", "!Shape_Length!", "PYTHON_9.3")

    # Create a 100 meter buffer arounds the islands
    arcpy.Buffer_analysis("islands", "buffered_islands", "100 Meters", "FULL", "ROUND")

    # Cleanup
    remove_intermediary_layers(["islands_proj","islands_dissolved",
                                "islands_gt_0", "islands_gte_1000m"])

# Compute the CII score per LTS1-2 island
def compute_CII_per_island():
    # Compute the CII score per island as zonal statistics
    arcpy.CheckOutExtension("Spatial")
    arcpy.sa.ZonalStatisticsAsTable("buffered_islands", "STRONG", "cii_overall_score_ras1",
                                    "islands_with_CII_scores_table", "DATA", "MEAN")
    # Rename field MEAN to CII_Score_Overall
    arcpy.AlterField_management("islands_with_CII_scores_table", "MEAN", "CII_Score_Overall")
    # Join the resulting table back to the original islands feature class
    arcpy.AddJoin_management("islands", "STRONG", "islands_with_CII_scores_table", "STRONG", "KEEP_ALL")
    # Save to a new feature class
    arcpy.CopyFeatures_management("islands", "islands_with_score_with_nulls")
    arcpy.RemoveJoin_management("islands")

    # Remove any islands where the CII_Score_Overall is null ("> 0" does that)
    # Note: I did it differently from the other ones, because CopyFeatures_management()
    #       was not dropping the nulls for some reason
    arcpy.Select_analysis("islands_with_score_with_nulls", "islands_with_score", 'islands_with_CII_scores_table_CII_Score_Overall > 0')

    # Delete some unnecessary fields
    drop_fields = ["islands_with_CII_scores_table_OBJECTID","islands_with_CII_scores_table_STRONG",
                  "islands_with_CII_scores_table_COUNT", "islands_with_CII_scores_table_AREA"]
    arcpy.DeleteField_management("islands_with_score", drop_fields)

    # Rename some fields to their alias, to get rid of exagerated long names
    field_list = arcpy.ListFields("islands_with_score")
    for field in field_list:
        print(field.name)
        if field.aliasName in ["STRONG", "Orig_Length", "CII_Score_Overall"]:
            arcpy.AlterField_management("islands_with_score", field.name, field.aliasName)

    # Remove intermediary layer
    remove_intermediary_layers(["islands_with_CII_scores_table", "islands_with_score_with_nulls"])

# Prepare the Non-Circuit Trails layer
def prep_trails():
    # Add new field "Trail_ID" and copy the OID in it for clarity
    arcpy.AddField_management("trails_proj", "Trail_ID", "LONG")
    arcpy.CalculateField_management("trails_proj", "Trail_ID", "!OID!", "PYTHON_9.3")
    # Delete some unnecessary fields
    dropFields = ["FolderPath","SymbolID", "AltMode", "Base", "Clamped", "Extruded", "Snippet", "PopupInfo"]
    arcpy.DeleteField_management("trails_proj", dropFields)

    # Clip to the boundaries of 4_counties_dissolved
    arcpy.SpatialJoin_analysis("trails_proj", "extent_4_counties", "trails",
                            "JOIN_ONE_TO_ONE", "KEEP_COMMON", match_option="INTERSECT")

    # Remove intermediary layers
    remove_intermediary_layers(["trails_proj"])


# Set the merge rules in the fieldMappings for a spatial join
def set_up_merge_rules(field_name, merge_rule, field_mappings):
    # Get the field map index of this field and get the field map
    field_index = field_mappings.findFieldMapIndex(field_name)
    field_map = field_mappings.getFieldMap(field_index)
    # Update the field map with the new merge rule (by default the merge rule is "First")
    field_map.mergeRule = merge_rule
    # Replace with the updated field map
    field_mappings.replaceFieldMap(field_index, field_map)

# For each trail, find all intersecting islands
def find_trail_island_intersections():
    # Create the field mapping object that will be used in the spatial join
    field_mappings = arcpy.FieldMappings()
    # Populate the field mapping object with the fields from both feature classes of interest
    field_mappings.addTable("trails")
    field_mappings.addTable("islands_with_score")
    #Set up merge rules
    # Orig_length -- we will sum up the length of all intersecting islands for each trail
    set_up_merge_rules("Orig_length","Sum", field_mappings)
    # STRONG (i.e., island ID) -- we will count the number of all intersecting islands for each trail
    set_up_merge_rules("STRONG", "Count", field_mappings)
    # CII_Score_Overall -- we will compute the CII score average among all intersecting islands for each trail
    set_up_merge_rules("CII_Score_Overall", "Mean", field_mappings)

    # Do the spatial join to find all the islands that intersect with each trail
    arcpy.SpatialJoin_analysis("trails", "islands_with_score", "trails_intersecting",
                               "JOIN_ONE_TO_ONE", "KEEP_ALL", field_mappings, "INTERSECT", search_radius="50 Meters")
    # Rename fields
    arcpy.AlterField_management("trails_intersecting", "Orig_length", "Length_of_All_Islands", "Length_of_All_Islands")
    arcpy.AlterField_management("trails_intersecting", "STRONG", "Num_of_Islands", "Num_of_Islands")
    arcpy.AlterField_management("trails_intersecting", "CII_Score_Overall", "Trail_CII_Score", "Trail_CII_Score")
    # Delete an unnecessary field
    drop_fields = ["TARGET_FID"]
    arcpy.DeleteField_management("trails_intersecting", drop_fields)
    # Remove intermediary layer
    remove_intermediary_layers([])

# Keep only the trails that intersect with 2 islands or more
def filter_2_or_more_islands():
    #Select by Attribute trails that intersect with 2 islands or more
    arcpy.SelectLayerByAttribute_management("trails_intersecting", "NEW_SELECTION", "Num_of_Islands >=2")
    # Save to a new feature class and do some clean up
    arcpy.CopyFeatures_management("trails_intersecting", "trails_intersecting_gte_2")
    arcpy.SelectLayerByAttribute_management("trails_intersecting", "CLEAR_SELECTION")

# Compute the final score for each Non-Circuit Trail
def compute_trail_scores():
    # Add new field "Total_connectivity_score" where we will compute the
    # total connectivity score for each trail
    arcpy.AddField_management("trails_intersecting_gte_2", "Total_connectivity_score", "DOUBLE")

    #Get the maximum values in the whole table for relevant attribute
    length_of_all_islands_max = get_max("trails_intersecting","Length_of_All_Islands")
    num_of_islands_max = get_max("trails_intersecting","Num_of_Islands")
    trail_CII_score_max = get_max("trails_intersecting","Trail_CII_Score")
    #print(length_of_all_islands_max)
    #print(num_of_islands_max)
    #print(trail_CII_score_max)
    # Put together the overall score formula and apply it
    expr = ("(((!Length_of_all_Islands! /" + str(length_of_all_islands_max) +
            " + !Num_of_Islands! / " + str(num_of_islands_max) +
            " + !Trail_CII_Score!/" + str(trail_CII_score_max) +
            ")/3)*20)")
    #print(expr)
    arcpy.CalculateField_management("trails_intersecting_gte_2", "Total_connectivity_score",
                                    expr, "PYTHON_9.3")

# Rank a feature class features according to a specific attribute value
def generate_ranked_subset(in_feature_class, ranking_attribute, out_feature_class):
    # Sort the attribute table
    arcpy.Sort_management(in_feature_class, out_feature_class, [[ranking_attribute, "DESCENDING"]])
    # Add a Rank attribute and populate it
    arcpy.AddField_management(out_feature_class, "Rank", "LONG")
    arcpy.CalculateField_management(out_feature_class, "Rank", "!OBJECTID!", "PYTHON_9.3")
    # Also generate a separate feature class with the top 20 values
    arcpy.SelectLayerByAttribute_management(out_feature_class, "NEW_SELECTION", "Rank <= 20")
    arcpy.CopyFeatures_management(out_feature_class, out_feature_class + "_Top20" )
    arcpy.SelectLayerByAttribute_management(out_feature_class, "CLEAR_SELECTION")

# Generate trail feature classes ranked by the final overall score or only by the length of all intersecting islands
def generate_ranked_subsets():
    generate_ranked_subset("trails_intersecting_gte_2", "Total_connectivity_score", "trails_top_score_ranked")
    generate_ranked_subset("trails_intersecting_gte_2", "Length_of_All_Islands", "trails_longest_islands_ranked")

# Generate scored trail features classes for each county
def generate_LTS3_subsets_per_county():
    # Use a spatial join to add the name of the county for each trail
    arcpy.SpatialJoin_analysis("trails_intersecting_gte_2", boundaries_4_PA_counties, "trails_intersect_gte2_counties",
                                "JOIN_ONE_TO_ONE", "KEEP_all", match_option="INTERSECT")
    # Generate one feature class per county
    for county in county_list:
        expr = "CO_NAME = '" + county + "'"
        print(expr)
        arcpy.SelectLayerByAttribute_management("trails_intersect_gte2_counties",
                                                "NEW_SELECTION", expr)
        arcpy.CopyFeatures_management("trails_intersect_gte2_counties", "trails_intersect_gte_2_" + county)
        arcpy.SelectLayerByAttribute_management("trails_intersect_gte2_counties", "CLEAR_SELECTION")

# Rank each county-specific trail feature class
def generate_ranked_subsets_per_county():
    for county in county_list:
        generate_top_ranked_subset("trails_intersect_gte_2_" + county, "Total_connectivity_score", "trails_top_score_ranked_" + county)



# ***************************************
# Begin Main
print_time_stamp("Start")
#if COMPUTE_FROM_SCRATCH_OPTION == "yes":
#    prep_gdb()
#load_ancillary_layers()
set_up_env()
#prep_gdb()
#load_main_data()
if COMPUTE_FROM_SCRATCH_OPTION == "yes":
    #prep_islands()
    #compute_CII_per_island()
    #prep_trails()
    #find_trail_island_intersections()
    #filter_2_or_more_islands()
#compute_trail_scores()
#generate_ranked_subsets()
#generate_LTS3_subsets_per_county()
#generate_ranked_subsets_per_county()
print_time_stamp("Done")
