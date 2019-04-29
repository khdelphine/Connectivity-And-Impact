
# ***************************************
# ***Overview***
# Script name: community_impact_index.py
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
# Command: execfile(r'C:\Users\delph\Desktop\Github_repos\Connectivity-And-Impact\community_impact_index.py')
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
    arcpy.env.snapraster = current_extent
    arcpy.env.outputCoordinateSystem = current_extent
    arcpy.env.cellSize = 30

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

def prep_idp_dataset():
    # Local variables
    ipd =  orig_datasets_path + "\\CII\\DVRPC_2016_Indicators_of_Potential_Disadvantage\\DVRPC_2016_Indicators_of_Potential_Disadvantage.shp"
    ipd_clipped = gdb_output + "\\ipd_clipped"
    ipd_ras = gdb_output + "\\ipd_ras"
    ipd_score_ras = gdb_output + "\\ipd_score_ras"

    # Load the feature class into the MXD
    arcpy.MakeFeatureLayer_management(ipd, "idp")
    # NO need to reproject (already in NAD 1983 UTM Zone 18N)
    # Clip to the boundaries of 4_counties_dissolved
    arcpy.SpatialJoin_analysis(ipd, extent_4_counties, ipd_clipped,
                            "JOIN_ONE_TO_ONE", "KEEP_COMMON", match_option="HAVE_THEIR_CENTER_IN")
    # Convert into a raster
    arcpy.PolygonToRaster_conversion (ipd_clipped, "IPD_Score", ipd_ras)

    # reclassify the raster to 1-to-20 score using the Jenks natural breaks classification
    arcpy.CheckOutExtension("Spatial")
    outslice = arcpy.sa.Slice(ipd_ras, 20, "NATURAL_BREAKS")
    outslice.save(ipd_score_ras)
    # Display the resulting raster (note that the tool demands a slightly different name for the layer)
    arcpy.MakeRasterLayer_management(ipd_score_ras, "ipd_score_ras1")

    # Cleanup
    remove_intermediary_layers(["idp","ipd_clipped", "ipd_ras"])

def prep_pop_density_dataset():
    # Local variables
    pa_census_tracts_orig =  orig_datasets_path + "\\CII\\ACS_2016_population_est\\tl_2016_42_tract\\tl_2016_42_tract.shp"
    population_table_orig =  orig_datasets_path + "\\CII\\ACS_2016_population_est\\ACS_16_5YR_B01003\\ACS_16_5YR_B01003_with_ann.csv"
    pa_census_tracts_proj = gdb_output + "\\pa_census_tracts_proj"
    pa_census_tracts_clipped = gdb_output + "\\pa_census_tracts_clipped"
    pop_table = gdb_output + "\\pop_table"
    tracts_with_pop = gdb_output + "\\tracts_with_pop"
    pop_density_ras = gdb_output + "\\pop_density_ras"
    pop_density_score_ras = gdb_output + "\\pop_density_score_ras"

    # Load the feature class and table into the MXD
    arcpy.MakeFeatureLayer_management(pa_census_tracts_orig, "pa_census_tracts_orig")

    # Reproject to NAD 1983 UTM Zone 18N (No need for datum transformation)
    target_spatial_reference = arcpy.SpatialReference('NAD 1983 UTM Zone 18N')
    arcpy.Project_management(pa_census_tracts_orig, pa_census_tracts_proj, target_spatial_reference)

    # Clip to the boundaries of 4_counties_dissolved
    arcpy.SpatialJoin_analysis(pa_census_tracts_proj, extent_4_counties, "pa_census_tracts_clipped",
                              "JOIN_ONE_TO_ONE", "KEEP_COMMON", match_option="HAVE_THEIR_CENTER_IN")
    # Remove the extra tract that got included because of its weirdly-placed centroid
    # XXX This does not work the way it should XXX
    arcpy.SelectLayerByAttribute_management("pa_census_tracts_clipped", "NEW_SELECTION",
                                            "GEOID <> '42101006500'")
    # Save to a new feature class and do some clean up:
    arcpy.CopyFeatures_management("pa_census_tracts_clipped", "pa_census_tracts_clipped1")
    arcpy.SelectLayerByAttribute_management("pa_census_tracts_clipped", "CLEAR_SELECTION")

    # Import the table with the ACS Total Population data
    arcpy.TableToTable_conversion(population_table_orig, gdb_output, 'pop_table')

    # Join the table to the Census tracts:
    arcpy.AddJoin_management("pa_census_tracts_clipped1", "GEOID", pop_table, "GEO_id2", "KEEP_ALL")
    arcpy.CopyFeatures_management("pa_census_tracts_clipped1", tracts_with_pop)
    arcpy.RemoveJoin_management("pa_census_tracts_clipped1")

    # Add new Long field "TotalPop" and put the value of String field HD01_VD01:
    arcpy.AddField_management(tracts_with_pop, "TotalPop", "Double")
    arcpy.CalculateField_management(tracts_with_pop, "TotalPop",
                                    "!pop_table_HD01_VD01!",
                                    "PYTHON_9.3")

    # Add new Long field "AlandSqKm" and put in it the value of field
    # pa_census_tracts_clipped_ALAND converted to sq km:
    arcpy.AddField_management(tracts_with_pop, "AlandSqKm", "Double")
    arcpy.CalculateField_management(tracts_with_pop, "AlandSqKm",
                                    "!pa_census_tracts_clipped1_ALAND! / 1000000",
                                    "PYTHON_9.3")

    # Add new field "PopDensity" and put in it TotalPop divided by AlandSqKm
    arcpy.AddField_management(tracts_with_pop, "PopDensity", "Double")
    arcpy.CalculateField_management(tracts_with_pop, "PopDensity",
                                    "!TotalPop! / !AlandSqKm!",
                                    "PYTHON_9.3")

    # Convert into a raster
    arcpy.PolygonToRaster_conversion (tracts_with_pop, "PopDensity", pop_density_ras)

    # reclassify the raster to 1-to-20 score using the Jenks natural breaks classification
    arcpy.CheckOutExtension("Spatial")
    outslice = arcpy.sa.Slice(pop_density_ras, 20, "NATURAL_BREAKS")
    outslice.save(pop_density_score_ras)
    # Display the resulting raster (note that the tool demands a slightly different name for the layer)
    arcpy.MakeRasterLayer_management(pop_density_score_ras, "pop_density_score_ras1")

    # Cleanup
    remove_intermediary_layers(["pa_census_tracts_orig","pa_census_tracts_proj",
                                "pa_census_tracts_clipped", "pa_census_tracts_clipped1", "pop_table", "tracts_with_pop","pop_density_ras"
                                ])

def prep_employment_dataset():
    # Local variables
    employment_clipped = data_path + "\\XXXstop_gap.gdb\\Employment_BusinessPatternZip_with_pop_DVRPC_Counties"

    # Display the raster
    arcpy.MakeFeatureLayer_management(employment_clipped, "employment_clipped")

    # Convert into a raster
    arcpy.PolygonToRaster_conversion ("employment_clipped", "Emp_density",
                                          "employment_ras")
    # Clip the raster to the shape of the 4 counties
    arcpy.Clip_management("employment_ras", "#", "employment_clipped_ras",
                    extent_4_counties, "#", "ClippingGeometry")

    # Reclassify the raster to 1-to-20 score using the Jenks natural breaks classification
    arcpy.CheckOutExtension("Spatial")
    outslice = arcpy.sa.Slice("employment_clipped_ras", 20, "NATURAL_BREAKS")
    outslice.save("employment_score_ras")
    # Display the resulting raster
    arcpy.MakeRasterLayer_management("employment_score_ras", "employment_score_ras1")

    # Cleanup
    remove_intermediary_layers(["employment_clipped","employment_ras", "employment_clipped_ras"])

def prep_circuit_trails_dataset():
    # Local variables
    circuit_trails_orig =  orig_datasets_path + "\\CII\\DVRPC_Circuit_Trails_20190328\\DVRPC_Circuit_Trails.shp"
    circuit_trails = gdb_output + "\\circuit_trails"
    circuit_trails_distance_ras = gdb_output + "\\circuit_trails_distance_ras"
    circuit_trails_score_ras = gdb_output + "\\circuit_trails_score_ras"
    # Load the feature class into the MXD
    arcpy.MakeFeatureLayer_management(circuit_trails_orig, "circuit_trails_orig")

    # Remove the partial trolley data present in the dataset
    arcpy.SelectLayerByAttribute_management("circuit_trails_orig", "NEW_SELECTION",
                                            "Circuit = 'Existing' OR Circuit = 'In Progress' ")
    # Save to a new feature class and do some clean up:
    arcpy.CopyFeatures_management("circuit_trails_orig", circuit_trails)
    arcpy.SelectLayerByAttribute_management("circuit_trails_orig", "CLEAR_SELECTION")

    # Compute the Euclidean distance raster to the rail stops
    outEucDistance = arcpy.sa.EucDistance(circuit_trails)
    outEucDistance.save(circuit_trails_distance_ras)
    # Display the resulting raster (note that the tool demands a slightly different name for the layer)
    arcpy.MakeRasterLayer_management(circuit_trails_distance_ras, "circuit_trails_distance_ras1")

    # Reclassify the raster based on chosen thresholds
    # First, convert distances in miles into meters:
    one_mile = 1609.34
    # Approximate maximun distance within the extent (in meters) for the upper bound
    max_distance = 134000
    circuit_remap_range = arcpy.sa.RemapRange([[0, one_mile , 20],
                                                [one_mile, max_distance, 1]])
    # Perform the reclassification and display it
    outReclassRaster = arcpy.sa.Reclassify(circuit_trails_distance_ras, "Value", circuit_remap_range)
    outReclassRaster.save(circuit_trails_score_ras)
    arcpy.MakeRasterLayer_management(circuit_trails_score_ras, "circuit_trails_score_ras1")

    # Clean up
    remove_intermediary_layers(["circuit_trails_orig", "circuit_trails", "circuit_trails_distance_ras1"])

def prep_0_vehicle_dataset():
    commuting_table_orig =  orig_datasets_path + "\\CII\\Vehicle_available\\ACS_17_5YR_S0801\\ACS_17_5YR_S0801_with_ann.csv"

    # Load the feature class and table into the MXD
    arcpy.MakeFeatureLayer_management("pa_census_tracts_clipped1", "pa_census_tracts_clipped1")

    # Import the table with ACS Commuting data
    arcpy.TableToTable_conversion(commuting_table_orig, gdb_output, "commuting_table")

    # Join the table to the Census tracts:
    arcpy.AddJoin_management("pa_census_tracts_clipped1", "GEOID", "commuting_table", "GEO_id2", "KEEP_ALL")
    arcpy.CopyFeatures_management("pa_census_tracts_clipped1", "tracts_with_commuting")
    arcpy.RemoveJoin_management("pa_census_tracts_clipped1")

    # Add new Float field "NoVehiclePct" and put the value of String field HC01_EST_VC59:
    arcpy.AddField_management("tracts_with_commuting", "NoVehiclePct", "Float")
    expression = "convert_value(!commuting_table_HC01_EST_VC59!)"
    codeblock = """def convert_value(str_value):
        if str_value == "-":
            return 0
        else:
            return float(str_value)"""

    arcpy.CalculateField_management("tracts_with_commuting", "NoVehiclePct",
                                    expression, "PYTHON_9.3", codeblock)
    # Convert into a raster
    arcpy.PolygonToRaster_conversion ("tracts_with_commuting", "NoVehiclePct",
                                      "no_vehicle_available_ras")

    # reclassify the raster to 1-to-20 score using the Jenks natural breaks classification
    arcpy.CheckOutExtension("Spatial")
    outslice = arcpy.sa.Slice("no_vehicle_available_ras", 20, "NATURAL_BREAKS")
    outslice.save("no_vehicle_score_ras")
    # Display the resulting raster (note that the tool demands a slightly different name for the layer)
    arcpy.MakeRasterLayer_management("no_vehicle_score_ras", "no_vehicle_score_ras1")

    # Cleanup
    remove_intermediary_layers(["pa_census_tracts_clipped1","commuting_table",
                                "tracts_with_commuting", "no_vehicle_available_ras"])

def prep_rail_dataset():
    # Local variables
    rail_stops_orig =  orig_datasets_path + "\\CII\\DVRPC_Passenger_Rail_Stations\\DVRPC_Passenger_Rail_Stations.shp"
    rail_stops_distance_ras = gdb_output + "\\rail_stops_distance_ras"
    rail_stops_proj = gdb_output + "\\rail_stops_proj"
    rail_stops_proj2 = gdb_output + "\\rail_stops_proj2"
    rail_score_ras = gdb_output + "\\rail_score_ras"

    # Load the feature class into the MXD
    arcpy.MakeFeatureLayer_management(rail_stops_orig, "rail_stops_orig")
    # Reproject to NAD 1983 UTM Zone 18N
    target_spatial_reference = arcpy.SpatialReference('NAD 1983 UTM Zone 18N')
    arcpy.Project_management(rail_stops_orig, rail_stops_proj, target_spatial_reference, "WGS_1984_(ITRF00)_To_NAD_1983")

    # Remove the partial trolley data present in the dataset
    arcpy.SelectLayerByAttribute_management("rail_stops_proj", "NEW_SELECTION", "Type <>'Surface Trolley'")
    # Save to a new feature class and do some clean up:
    arcpy.CopyFeatures_management("rail_stops_proj", rail_stops_proj2)
    arcpy.SelectLayerByAttribute_management("rail_stops_proj", "CLEAR_SELECTION")

    # Compute the Euclidean distance raster to the rail stops
    outEucDistance = arcpy.sa.EucDistance(rail_stops_proj2)
    outEucDistance.save(rail_stops_distance_ras)
    # Display the resulting raster (note that the tool demands a slightly different name for the layer)
    arcpy.MakeRasterLayer_management(rail_stops_distance_ras, "rail_stops_distance_ras1")

    # Reclassify the raster based on chosen thresholds
    # First, convert distances in miles into meters:
    one_mile = 1609.34
    five_miles = 5 * 1609.34
    # Approximate maximun distance within the extent (in meters) for the upper bound
    max_distance = 134000
    transit_remap_range = arcpy.sa.RemapRange([[0, one_mile , 1],
                                                [one_mile, five_miles, 20],
                                                [five_miles, max_distance, 10]])
    # Perform the reclassification and display it
    outReclassRaster = arcpy.sa.Reclassify(rail_stops_distance_ras, "Value", transit_remap_range)
    outReclassRaster.save(rail_score_ras)
    arcpy.MakeRasterLayer_management(rail_score_ras, "rail_score_ras1")
    # Clean up
    remove_intermediary_layers(["rail_stops_orig", "rail_stops_proj", "rail_stops_proj2", "rail_stops_distance_ras1"])

def prep_trolley_dataset():
    # Local variables
    trolley_stops_orig =  orig_datasets_path + "\\CII\\SEPTA__Trolley_Stops\\SEPTA__Trolley_Stops.shp"
    trolley_stops_distance_ras = gdb_output + "\\trolley_stops_distance_ras"
    trolley_stops_proj = gdb_output + "\\trolley_stops_proj"
    trolley_score_ras = gdb_output + "\\trolley_score_ras"

    # Load the feature class into the MXD
    arcpy.MakeFeatureLayer_management(trolley_stops_orig, "trolley_stops_orig")
    # Reproject to NAD 1983 UTM Zone 18N
    target_spatial_reference = arcpy.SpatialReference('NAD 1983 UTM Zone 18N')
    arcpy.Project_management(trolley_stops_orig, trolley_stops_proj, target_spatial_reference, "WGS_1984_(ITRF00)_To_NAD_1983")

    # Compute the Euclidean distance raster to the trolley stops
    outEucDistance = arcpy.sa.EucDistance(trolley_stops_proj)
    outEucDistance.save(trolley_stops_distance_ras)
    # Display the resulting raster (note that the tool demands a slightly different name for the layer)
    arcpy.MakeRasterLayer_management(trolley_stops_distance_ras, "trolley_stops_distance_ras1")

    # Reclassify the raster based on chosen thresholds
    # First, convert distances in miles into meters:
    one_mile = 1609.34
    five_miles = 5 * 1609.34
    # Approximate maximun distance within the extent (in meters) for the upper bound
    max_distance = 134000
    transit_remap_range = arcpy.sa.RemapRange([[0, one_mile , 1],
                                                [one_mile, five_miles, 20],
                                                [five_miles, max_distance, 10]])
    # Perform the reclassification and display it
    outReclassRaster = arcpy.sa.Reclassify(trolley_stops_distance_ras, "Value", transit_remap_range)
    outReclassRaster.save(trolley_score_ras)
    # Clean up
    arcpy.MakeRasterLayer_management(trolley_score_ras, "trolley_score_ras1")
    remove_intermediary_layers(["trolley_stops_orig","trolley_stops_proj", "trolley_stops_distance_ras1"])

def prep_bus_dataset():
    # Local variables
    bus_stops_orig =  orig_datasets_path + "\\CII\\SEPTA__Bus_Stops\\SEPTA__Bus_Stops.shp"
    bus_stops_distance_ras = gdb_output + "\\bus_stops_distance_ras"
    bus_stops_proj = gdb_output + "\\bus_stops_proj"
    bus_score_ras = gdb_output + "\\bus_score_ras"

    # Load the feature class into the MXD
    arcpy.MakeFeatureLayer_management(bus_stops_orig, "bus_stops_orig")
    # Reproject to NAD 1983 UTM Zone 18N
    target_spatial_reference = arcpy.SpatialReference('NAD 1983 UTM Zone 18N')
    arcpy.Project_management(bus_stops_orig, bus_stops_proj, target_spatial_reference, "WGS_1984_(ITRF00)_To_NAD_1983")

    # Compute the Euclidean distance raster to the bus stops
    outEucDistance = arcpy.sa.EucDistance(bus_stops_proj)
    outEucDistance.save(bus_stops_distance_ras)
    arcpy.MakeRasterLayer_management(bus_stops_distance_ras, "bus_stops_distance_ras1")

    # Reclassify the raster based on chosen thresholds
    # First, convert distances in miles into meters:
    one_mile = 1609.34
    five_miles = 5 * 1609.34
    # Approximate maximun distance within the extent (in meters) for the upper bound
    max_distance = 134000
    transit_remap_range = arcpy.sa.RemapRange([[0, one_mile , 1],
                                                [one_mile, five_miles, 20],
                                                [five_miles, max_distance, 10]])
    # Perform the reclassification and display it
    outReclassRaster = arcpy.sa.Reclassify(bus_stops_distance_ras, "Value", transit_remap_range)
    outReclassRaster.save(bus_score_ras)
    arcpy.MakeRasterLayer_management(bus_score_ras, "bus_score_ras1")

    # Clean up
    remove_intermediary_layers(["bus_stops_orig","bus_stops_proj", "bus_stops_distance_ras1"])

def prep_nata_resp_dataset():
    # Local variables
    ejscreen_orig = data_path + "\\XXXstop_gap.gdb\\Health_JSCREEN_Tract_DVRPC_9_Counties_proj"

    # Load the feature class and table into the MXD
    arcpy.MakeFeatureLayer_management(ejscreen_orig, "ejscreen_orig")

    # Clip to the boundaries of 4_counties_dissolved
    arcpy.SpatialJoin_analysis(ejscreen_orig, extent_4_counties, "ejscreen_clipped",
                              "JOIN_ONE_TO_ONE", "KEEP_COMMON", match_option="HAVE_THEIR_CENTER_IN")
    # Convert into a raster
    arcpy.PolygonToRaster_conversion ("ejscreen_clipped", "RESP",
                                          "nata_resp_ras")

    # reclassify the raster to 1-to-20 score using the Jenks natural breaks classification
    arcpy.CheckOutExtension("Spatial")
    outslice = arcpy.sa.Slice("nata_resp_ras", 20, "NATURAL_BREAKS")
    outslice.save("nata_resp_score_ras")
    # Display the resulting raster
    arcpy.MakeRasterLayer_management("nata_resp_score_ras", "nata_resp_score_ras1")

    # Cleanup
    remove_intermediary_layers(["ejscreen_orig","ejscreen_clipped","nata_resp_ras"])

def prep_obesity_dataset():
    obesity_ras = data_path + "\\XXXstop_gap.gdb\\Obesity_PA_normalized_ras"

    # Display the raster
    arcpy.MakeRasterLayer_management(obesity_ras, "obesity_ras1")

    # reclassify the raster to 1-to-20 score using the Jenks natural breaks classification
    arcpy.CheckOutExtension("Spatial")
    outslice = arcpy.sa.Slice("obesity_ras1", 20, "NATURAL_BREAKS")
    outslice.save("obesity_score_ras")
    # Display the resulting raster (note that the tool demands a slightly different name for the layer)
    arcpy.MakeRasterLayer_management("obesity_score_ras", "obesity_score_ras1")

    # Cleanup
    remove_intermediary_layers(["obesity_ras1"])

def compute_density_scores():
    # Compute score raster for density
    total_ras = (arcpy.Raster("pop_density_score_ras1")*0.67 +
                 arcpy.Raster("employment_score_ras1")*0.33)
    total_ras.save("density_score_ras")
    # Display the new raster
    arcpy.MakeRasterLayer_management("density_score_ras", "density_score_ras1")

def compute_transportation_scores():
    # Compute score raster for transit
    total_ras = (arcpy.Raster("circuit_trails_score_ras1")*0.5 +
                 arcpy.Raster("no_vehicle_score_ras1")*0.27 +
                 arcpy.Raster("rail_score_ras1")*0.13 +
                 arcpy.Raster("trolley_score_ras1")*0.07 +
                 arcpy.Raster("bus_score_ras1")*0.03)
    total_ras.save("transportation_score_ras")
    # Display the new raster
    arcpy.MakeRasterLayer_management("transportation_score_ras", "transportation_score_ras1")

def compute_health_scores():
    # Compute score raster for health / environment
    total_ras = (arcpy.Raster("obesity_score_ras1")*0.5 +
                 arcpy.Raster("nata_resp_score_ras1")*0.5)
    total_ras.save("health_score_ras")
    # Display the new raster
    arcpy.MakeRasterLayer_management("health_score_ras", "health_score_ras1")

def compute_CII_overall_scores():
    # Compute score raster for Community Impact Index (CII) overall scores
    total_ras = (arcpy.Raster("ipd_score_ras1")*0.3 +
                 arcpy.Raster("density_score_ras1")*0.3 +
                 arcpy.Raster("transportation_score_ras1")*0.3 +
                 arcpy.Raster("health_score_ras1")*0.1)
    total_ras.save("cii_overall_score_ras")
    # Display the new raster
    arcpy.MakeRasterLayer_management("cii_overall_score_ras", "cii_overall_score_ras1")


def compute_all_aggregated_scores():
    compute_density_scores()
    compute_transportation_scores()
    compute_health_scores()
    compute_CII_overall_scores()

def prep_all_datasets():
    prep_idp_dataset()
    prep_pop_density_dataset()
    prep_employment_dataset()
    prep_circuit_trails_dataset()
    prep_0_vehicle_dataset()
    prep_rail_dataset()
    prep_trolley_dataset()
    prep_bus_dataset()
    prep_nata_resp_dataset()
    prep_obesity_dataset()


# ***************************************
# Begin Main
print_time_stamp("Start")
set_up_env()
prep_gdb()
prep_all_datasets()
compute_all_aggregated_scores()
print_time_stamp("Done")
