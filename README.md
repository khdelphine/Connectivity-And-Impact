# Bicycle Connectivity & Community Impact Analysis

## Starting Point
This work is based on the data produced by the DVRPC Bicycle LTS and Connectivity Analysis project (Moran, 2017), and more specifically on the following two datasets:
* Bike Stress LTS 1 & 2 Islands (DVRPC, 2017a): clusters of low-stress, highly bikable roads
* Bike Stress Suburban LTS 3 Connections (DVRPC, 2017b): medium-stress LTS3 road segments, ranked by connectivity level, in relation to LTS 1 & 2 islands.

## Goals
* Identify the non-circuit trails that: 
  * Connect the most LTS1-2 islands
  * Connect the maximum total length of LTS1-2 islands
  * Have the highest community impact
* Identify the LTS3 road segments that:
  * Have the highest connectivity level and
  * Have the highest community impact
* Produce results for:
  * The 4 Suburban Pennsylvania County as a whole 
  * Each county individually

## Essential Steps
### 1. Generate a Community Impact Index (CII)
**Criteria taken into account:**
* Equity -- Indicator of Perceived Disadvantage (DVRPC, 2016)
* Density -- both population and employment*  
* Transportation -- distance to  circuit trails, proportion of household with 0 vehicles available, distance to transit 
* Health -- obesity rate and rate of respiratory hazards


**Approach:** We turn all feature classes into rasters, reclassify those rasters into a 1-to-20 score rasters, and use map algebra to compute a total combined score raster. The scores are established as follows
* For most criteria, we use the Jenks natural breaks classification to create 20 classes.
* For Circuit trails:  under 1 mile: 20 points, above 1 mile 1 point. Rationale: growing the Circuit is a priority.
* Distance from transit:  under 1 mile: 1 points, between 1 and 5 miles 20 points, above 5 miles: 10 point. Rationale: between 1 and 5 miles, the impact would be the highest as new biking infrastructure could help residents reach transit stations and stops by bike. Beyond 5 miles, residents don’t have access to transit, so they would benefit from improved biking infrastructure, but the impact would be more diluted.


**Weights for the Aggregated CII Scores:**
* Indicator of Perceived Disadvantage: 30%
* Density: 30% 
  * Population density: 20% 
  * Employment density: 10% 
* Transportation: 30% 
  * Circuit trails: 15% 
  * 0 Vehicule available: 8% 
  * Distance from transit: 7% 
    * Rail: 4%, trolley: 2% and bus: 1% 
* Health: 10% 
  * Obesity: 5% 
  * Respiratory hazards: 5% 

**Output**: CII score raster.

### 2. Identify high-priority non-circuit trails
* Create a buffer of 100 meters around the LTS1-2 islands.
* Use Zonal Statistics As Table to compute a CII score for every buffered island, using the Mean to aggregate the scores.
* Perform a Spatial Join to join the islands to the non-circuit trails, using the option ONE-to-ONE. Use merge rules to (1) count the number of islands intersected by each trail,  (2) sum up the total length that those islands represent, and (3) average the islands’ CII scores. A radius of 50 meters is used.
* Compute an overall 1-to-20 score for each trail based on: ⅓ for the number of islands intersected, ⅓ for the total islands’ length and ⅓ for their CII scores.   
* Output: a ranked list of the trails with the highest overall scores. 


### 3. Identify high-priority LTS3 road segments* 
* Select the top 30% highest connectivity LTS3 segments (based on how many Census block connections they could enable).
* Create a 1-mile buffer around them, as a rough method to account for the target census blocks they connect.
* Use Zonal Statistics As Table to compute the CII score for each buffered LTS3 segment.
* Compute an overall 1-to20 score composed of: ⅓ for the connectivity score and ⅔ for the CII score. 
* Select the top third LTS3 segments based on their overall scores.
* Output: a new subset of 10% highest priority LTS3 segments.
* Note: it would have been more accurate to use the CII scores for the Census blocks that each LTS3 segment connects, but we did not have access to that data.

## References
Moran, S. (2017, November 27). DVRPC Bicycle LTS and Connectivity Analysis Documentation [Memo]. Retrieved from
https://www.dvrpc.org/webmaps/BikeStress/documentation.pdf

