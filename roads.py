
# ***************************************
# ***Overview***
# Script name: roads.py
# Purpose: This Arcpy script identifies the LTS3 road segments with the highest connectivity and community impact score.
# Project: Connectivity and community impact analysis in Arcpy for potential bicycle infrastructure improvements.
# Extent: 4 PA Counties in Philadelphia suburbs.
# Last updated: May 11, 2019
# Author: Delphine Khanna
# Organization: Bicycle Coalition of Greater Philadelphia
# Note: This Arcpy script is meant to run in ArcGIS Desktop. It is NOT optimized for complete unsupervised automation.
# Commands for the ArcGIS Python interpreter:
#    1. To get into the current directory: import os; os.chdir("C:\Users\delph\Desktop\Github_repos\Connectivity-And-Impact")
#    2. Execute this file: execfile(r'roads.py')
# ***************************************

# Import Arcpy modules:
import arcpy
import arcpy.sa # Spatial Analyst
import arcpy.da # Data Access

# Import local modules:
from config import *
from utilities import *

num_of_score_tables = 0

# *****************************************
# Functions

# Load the main datasets
def load_main_data():
    # Load the LTS3 feature class into the MXD
    arcpy.MakeFeatureLayer_management(lts3_orig, "lts3_orig")
    # NO need to reproject (already in NAD 1983 UTM Zone 18N)
    # Load the CII overall score raster into the MXD
    arcpy.MakeRasterLayer_management(cii_overall_score_ras, "cii_overall_score_ras1")

    # We have the option to load the LTS3 layer with the CII scores instead of regenerating it:
    if COMPUTE_FROM_SCRATCH_OPTION == "no":
        arcpy.MakeFeatureLayer_management("aggregated_lts3_top30pct_with_cii_scores",
                                        "aggregated_lts3_top30pct_with_cii_scores")


# Select the top 30% LTS3 road segments
def select_top30pct_lts3():
    # Select the top 30% LTS3 road segments using the attribute Top30percent
    arcpy.SelectLayerByAttribute_management("lts3_orig", "NEW_SELECTION", "Top30perce = 1")
    # Save to a new feature class and do some clean up
    arcpy.CopyFeatures_management("lts3_orig", "lts3_top30pct")
    arcpy.SelectLayerByAttribute_management("lts3_orig", "CLEAR_SELECTION")

# Create a 1 mile meter buffer arounds every LTS3 road segment
def buffer_lts3():
    arcpy.Buffer_analysis("lts3_top30pct", "lts3_top30pct_buffered", "1609.34 Meters", "FULL", "ROUND")

# Compute CII scores per LTS3 road segment. The loop is a work around the fact that
# arcpy.sa.ZonalStatisticsAsTable() does not work for overlapping zone.
def compute_CII_scores_per_lts3():
    # Prepare everything before the loop
    arcpy.CheckOutExtension("Spatial")
    arcpy.Delete_management("lts3_unprocessed")
    arcpy.CopyFeatures_management("lts3_top30pct_buffered", "lts3_unprocessed")
    # Rename the EDGE field to its simplest form
    field_list = arcpy.ListFields("lts3_unprocessed")
    for field in field_list:
        if field.aliasName == "EDGE":
            arcpy.AlterField_management("lts3_unprocessed", field.name, "EDGE")
            break

    # Initialize the number_of_rows variable and the "i" iteration counter
    num_of_rows = int(arcpy.GetCount_management("lts3_unprocessed")[0])
    i = 1

    # Loop to perform the Zonal Statistics as Table iteratively, processing each time them
    # subset of rows that were not already processed in the last iteration. It generates
    # multiple table output that will be merged later on in the function
    # aggregate_all_zonalTables()
    while num_of_rows > 0:
        # At each iteration we will generate a new lts3_with_CII_scores_table
        lts3_with_CII_scores_table  = gdb_output + "\\lts3_with_CII_scores_table" + str(i)
        # Compute the CII score per LTS3 segment as zonal statistics. The output is a table
        arcpy.sa.ZonalStatisticsAsTable("lts3_unprocessed", "EDGE", "cii_overall_score_ras1",
                                        lts3_with_CII_scores_table, "DATA", "MEAN")

        # Create a temporary feature class that contains the results of the Zonal Statistics tool
        lts3_table = "lts3_with_CII_scores_table"  + str(i)
        arcpy.AddJoin_management("lts3_unprocessed", "EDGE", lts3_table, "EDGE", "KEEP_ALL")
        arcpy.CopyFeatures_management("lts3_unprocessed", "lts3_temp")
        # Remove the join and delete lts3_unprocessed
        arcpy.RemoveJoin_management("lts3_unprocessed") #Not needed?
        arcpy.Delete_management("lts3_unprocessed")

        # Put any LTS3 segment that didn't not get processed in a new feature class
        # lts3_unprocessed. They can be recognized because some of their attributes are NULL.
        expr = "lts3_with_CII_scores_table" + str(i) + "_MEAN IS NULL"
        print(expr)
        arcpy.SelectLayerByAttribute_management("lts3_temp", "NEW_SELECTION", expr)
        arcpy.CopyFeatures_management("lts3_temp", "lts3_unprocessed")
        arcpy.SelectLayerByAttribute_management("lts3_temp", "CLEAR_SELECTION")

        # Delete all fields in new_lts3_unprocessed that came from lts3_with_CII_scores_table, so that
        # we start with a blank slate in the next round
        drop_fields = ["lts3_with_CII_scores_table" + str(i) + "_OBJECTID",
                       "lts3_with_CII_scores_table" + str(i) + "_EDGE",
                       "lts3_with_CII_scores_table" + str(i) + "_COUNT",
                       "lts3_with_CII_scores_table" + str(i) + "_AREA",
                       "lts3_with_CII_scores_table" + str(i) + "_MEAN"]
        arcpy.DeleteField_management("lts3_unprocessed", drop_fields)

        # Rename the EDGE field to its simplest form in lts3_unprocessed
        field_list = arcpy.ListFields("lts3_unprocessed")
        for field in field_list:
            if field.aliasName == "EDGE":
                print(field.name)
                arcpy.AlterField_management("lts3_unprocessed", field.name, "EDGE")
                break

        # Increment the counters
        num_of_rows = int(arcpy.GetCount_management("lts3_unprocessed")[0])
        i += 1
        print("num_of_rows: " + str(num_of_rows))
        print("i: "+ str(i))
    num_of_score_tables = i - 1

# Put all partial zonal tables back together
def aggregate_all_zonalTables():
    # Initialize local variables
    merge_list =[]
    # Only if entering the number of tables manually
    # num_of_score_tables=16
    for j in range(num_of_score_tables):
        merge_list.append("lts3_with_CII_scores_table"+ str(j+1))
    print(merge_list)
    arcpy.Merge_management(merge_list, "merged_lts3_with_CII_scores_table")
    arcpy.AddJoin_management("lts3_top30pct", "EDGE", "merged_lts3_with_CII_scores_table", "EDGE", "KEEP_ALL")
    arcpy.CopyFeatures_management("lts3_top30pct", "aggregated_lts3_top30pct_with_cii_scores")

    # Remove the join and delete lts3_unprocessed
    arcpy.RemoveJoin_management("lts3_top30pct")

# Compute the overall LTS3 scores
def compute_overall_scores():
    # Add a new field Total_Score, and put in it the sum of the CII score (normalized
    # by the max CII score) + the connectivity score (normalized by the max connectivity score).
    # The name of the attributes are MEAN and TOTAL, respectively.
    ##arcpy.AddField_management("aggregated_lts3_top30pct_with_cii_scores", "CII_Score", "Double")
    arcpy.CalculateField_management("aggregated_lts3_top30pct_with_cii_scores", "CII_Score",
                                    "!merged_lts3_with_CII_scores_table_MEAN!", "PYTHON_9.3")

    arcpy.AddField_management("aggregated_lts3_top30pct_with_cii_scores", "Connectivity_Score", "Double")
    total_max = get_max("aggregated_lts3_top30pct_with_cii_scores","lts3_top30pct_TOTAL")
    conn_score_norm_expr = "(float(!lts3_top30pct_TOTAL!) / " + str(total_max) + ")*20"
    arcpy.CalculateField_management("aggregated_lts3_top30pct_with_cii_scores", "Connectivity_Score",
                                        conn_score_norm_expr, "PYTHON_9.3")

    arcpy.AddField_management("aggregated_lts3_top30pct_with_cii_scores", "Overall_Score", "Double")
    #Aggregate the two scores: 2/3 CII score + 1/3 Connectivity score
    overall_score_expr = "(!CII_Score! * 0.67) + (!Connectivity_Score!*0.33)"
    arcpy.CalculateField_management("aggregated_lts3_top30pct_with_cii_scores", "Overall_Score",
                                        overall_score_expr, "PYTHON_9.3")

# Generate LTS3 subsets per county
def generate_LTS3_subsets_per_county():
    for county in county_list:
        expr = "lts3_top30pct_COUNTIES = '" + county + "'"
        print(expr)
        arcpy.SelectLayerByAttribute_management("aggregated_lts3_top30pct_with_cii_scores",
                                                "NEW_SELECTION", expr)
        arcpy.CopyFeatures_management("aggregated_lts3_top30pct_with_cii_scores", "lts3_with_cii_scores_" + county)
        arcpy.SelectLayerByAttribute_management("aggregated_lts3_top30pct_with_cii_scores", "CLEAR_SELECTION")

# Rank an LTS3 subsets according to a specific attribute and select the top third.
# Also select the top 20 rows.
def generate_top_ranked_subset(in_feature_class, ranking_attribute, out_feature_class):
    # Sort the feature class
    arcpy.Sort_management(in_feature_class, out_feature_class, [[ranking_attribute, "DESCENDING"]])
    # Add a rank attribute and populate it
    arcpy.AddField_management(out_feature_class, "Rank", "LONG")
    arcpy.CalculateField_management(out_feature_class, "Rank", "!OBJECTID!", "PYTHON_9.3")

    # Create a new feature class with the top third rows
    max_rank = get_max(out_feature_class,"Rank")
    one_third_rows = max_rank / 3
    print(one_third_rows)
    arcpy.SelectLayerByAttribute_management(out_feature_class, "NEW_SELECTION", "Rank <= " + str(one_third_rows))
    arcpy.CopyFeatures_management(out_feature_class, out_feature_class + "_top10pct" )
    arcpy.SelectLayerByAttribute_management(out_feature_class, "CLEAR_SELECTION")

    #  Create a new feature class with the top 20 rows
    arcpy.SelectLayerByAttribute_management(out_feature_class, "NEW_SELECTION", "Rank <= 20")
    arcpy.CopyFeatures_management(out_feature_class, out_feature_class + "_top20" )
    arcpy.SelectLayerByAttribute_management(out_feature_class, "CLEAR_SELECTION")

# Generate a top 10% subset for a specific county
def generate_LTS3_orig_10pct_subsets_per_county(county_name):
    # Select the top 10% LTS3 road segments using the original attribute Top10percent
    arcpy.SelectLayerByAttribute_management("lts3_with_cii_scores_" + county_name, "NEW_SELECTION",
                                            "lts3_top30pct_TOP10PERCE = 1")
    # Save to a new feature class and do some clean up
    arcpy.CopyFeatures_management("lts3_with_cii_scores_" + county_name,
                                  "lts3_orig_10pct_ranked_" + county_name)
    arcpy.SelectLayerByAttribute_management("lts3_with_cii_scores_" + county_name, "CLEAR_SELECTION")

# Generate top 10% subsets for all 4 counties and on two different sorting criteria
# (the overall score and the connectivity score only)
def generate_LTS3_10pct_subsets_per_county():
    for county in county_list:
        generate_top_ranked_subset("lts3_with_cii_scores_" + county, "Overall_Score",
                                    "lts3_overall_score_ranked_" + county)
        generate_LTS3_orig_10pct_subsets_per_county(county)


# ***************************************
# Begin Main
print_time_stamp("Start")
#if COMPUTE_FROM_SCRATCH_OPTION == "yes":
    #prep_gdb()
#load_ancillary_layers()
#set_up_env()
#load_main_data()
if COMPUTE_FROM_SCRATCH_OPTION == "yes":
    select_top30pct_lts3()
    buffer_lts3()
    compute_CII_scores_per_lts3()
    aggregate_all_zonalTables()
#compute_overall_scores()
#generate_LTS3_subsets_per_county()
#generate_LTS3_10pct_subsets_per_county()
print_time_stamp("Done")
