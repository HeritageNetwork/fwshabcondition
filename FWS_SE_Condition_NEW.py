import arcpy, os
from arcpy.sa import *

arcpy.env.extent = "1272796.01889252 837937.189808734 1293290.19762114 851783.705021468" # temporary
arcpy.env.workspace = r"S:\Projects\USFWS\SE_FWS_Habitat_2022\FWS_HabConScriptTesting"
arcpy.env.scratchWorkspace =r"S:\Projects\USFWS\SE_FWS_Habitat_2022\FWS_HabConScriptTesting\FWS_HabConScriptTesting.gdb"
arcpy.env.overwriteOutput =  True

# Check out any necessary licenses.
arcpy.CheckOutExtension("spatial")
#arcpy.CheckOutExtension("ImageExt")
#arcpy.CheckOutExtension("ImageAnalyst")

# Input Variables
GenerateTessellation100acres = r"S:\Projects\USFWS\SE_FWS_Habitat_2022\SE_FWS_HabitatCondition\SE_FWS_HabitatCondition.gdb\GenerateTessellation100acres"
combined_EVT_tif = r"S:\Projects\_Workspaces\Jordana_Anderson\SE_USFWS\FWS_SE_Condition\FWS_SE_Condition_testing\FWS_SE_Condition_testing.gdb\combined_EVT_Clip"
SE_FWS_HabitatCondition_gdb = r"S:\Projects\_Workspaces\Jordana_Anderson\SE_USFWS\FWS_SE_Condition\FWS_SE_Condition_testing\FWS_SE_Condition_testing.gdb"
#Reclass_LC201 = r"S:\Projects\USFWS\SE_FWS_Habitat_2022\SE_FWS_HabitatCondition\SE_FWS_HabitatCondition.gdb\Reclass_LC201"
hexclip = r"S:\Projects\USFWS\SE_FWS_Habitat_2022\FWS_HabConScriptTesting\FWS_HabConScriptTesting.gdb\hexclip"                             

dataLCM = r"S:\Data\NatureServe\Landscape_Condition\Americas_N_LCM_Cat100.tif"
dataRuderal = r"S:\Projects\USFWS\SE_FWS_Habitat_2022\SE_FWS_HabitatCondition\Ruderal_5cell_scaled.tif"
dataFireDep = r"S:\Data\External\LANDFIRE_Fire_Departure\LF2020_VDep_220_CONUS\LF2020_VDep_220_CONUS\Tif\LC20_VDep_220.tif"

#path = r"S:\Projects\_Workspaces\Jordana_Anderson\SE_USFWS\FWS_SE_Condition\FWS_SE_Condition_testing\FWS_SE_Condition_testing.gdb\combined_EVT_Clip"
value_list = []   

outExtractByMask = ExtractByMask(combined_EVT_tif, hexclip)  # THIS WILL LIKELY HAVE TO BE MODIFED FOR THE FULL SCRIPT!!!!
outExtractByMask1 = ExtractByAttributes(outExtractByMask, '"Value_1" <> 0') 
outExtractByMask1.save("EVTclip.tif")

with arcpy.da.SearchCursor("EVTclip.tif", ["Value"]) as cursor:
    for row in cursor:
        value_list.append(row[0])
print(value_list)

for index in value_list:
    columnValue = index
    print("working on EVT" + str(columnValue))
    
    # Process: Extract by Attributes (Extract by Attributes) (sa)
    print("- working on extracting the EVT data")
    nameEVT = "tmp_Extract_" + str(columnValue) + ".tif"
    w_clause = '"VALUE" = ' + "%s" %columnValue
    tmp_Extract_Value_tif = ExtractByAttributes(in_raster="EVTclip.tif", where_clause=w_clause)
    tmp_Extract_Value_tif.save(os.path.join(arcpy.env.workspace, nameEVT))

    # Select out the hexagons that overlap the EVT cells
    print("- intersecting the EVT layer with the hex grid")
    tmp_Value_raster2pt = fr"tmp_{columnValue}_raster2pt"
    arcpy.conversion.RasterToPoint(in_raster=tmp_Extract_Value_tif, out_point_features=tmp_Value_raster2pt, raster_field="VALUE")    
    hexgridselection = arcpy.management.SelectLayerByLocation(in_layer=[GenerateTessellation100acres], overlap_type="INTERSECT", select_features=tmp_Value_raster2pt, search_distance="", selection_type="NEW_SELECTION", invert_spatial_relationship="NOT_INVERT")
    hexgridselection = arcpy.conversion.FeatureClassToFeatureClass(in_features=hexgridselection, out_path=arcpy.env.workspace, out_name=f"hex100ac_{columnValue}", where_clause="", field_mapping="Shape_Length \"Shape_Length\" false true true 8 Double 0 0,First,#,GenerateTessellation100acres,Shape_Length,-1,-1;Shape_Area \"Shape_Area\" false true true 8 Double 0 0,First,#,GenerateTessellation100acres,Shape_Area,-1,-1;GRID_ID \"GRID_ID\" true true false 12 Text 0 0,First,#,GenerateTessellation100acres,GRID_ID,0,12", config_keyword="")[0]

    # Work on the LCM
    print("- calculating and summarizing the LCM values")
    tmp_Value_LCM_tif = fr"tmp_{columnValue}_LCM.tif"
    tmp_Value_LCM_tif = arcpy.sa.ExtractByMask(in_raster=dataLCM, in_mask_data=nameEVT)
    ZonalSt_Value_LCM = fr"ZonalSt_{columnValue}_LCM"
    arcpy.sa.ZonalStatisticsAsTable(in_zone_data=hexgridselection, zone_field="GRID_ID", in_value_raster=tmp_Value_LCM_tif,
                                    out_table=ZonalSt_Value_LCM, ignore_nodata="DATA", statistics_type="MEAN")
    arcpy.management.JoinField(in_data=hexgridselection, in_field="GRID_ID", join_table=ZonalSt_Value_LCM, join_field="GRID_ID", fields=["MEAN"])[0]
    arcpy.management.CalculateField(in_table=hexgridselection, field="scoreLCM", expression="round(!MEAN!,1)", field_type="DOUBLE")
    arcpy.management.DeleteField(hexgridselection, "MEAN")
    #arcpy.management.AlterField(hexgridselection, "MEAN", "scoreLCM", "LCM Score") 

    # Work on Invasive Risk score
    print("- calculating the invasive risk score")
    tmp_InvRisk_tif = fr"tmp_{columnValue}_Inv.tif"
    tmp_InvRisk_tif = arcpy.sa.ExtractByMask(in_raster=dataRuderal, in_mask_data=nameEVT)
    ZonalSt_Value_InvRisk = fr"ZonalSt_{columnValue}_InvRisk"
    arcpy.sa.ZonalStatisticsAsTable(in_zone_data=hexgridselection, zone_field="GRID_ID", in_value_raster=tmp_InvRisk_tif,
                                    out_table=ZonalSt_Value_InvRisk, ignore_nodata="DATA", statistics_type="MEAN")
    arcpy.management.JoinField(in_data=hexgridselection, in_field="GRID_ID", join_table=ZonalSt_Value_InvRisk, join_field="GRID_ID", fields=["MEAN"])[0]
    arcpy.management.CalculateField(in_table=hexgridselection, field="scoreInv", expression="round(!MEAN!,1)", field_type="DOUBLE")
    arcpy.management.DeleteField(hexgridselection, "MEAN")
    #arcpy.management.AlterField(hexgridselection, "MEAN", "scoreLCM", "LCM Score") 

    # calculating the mean condition/quality score
    arcpy.management.CalculateField(in_table=hexgridselection, field="scoreInvR", expression="Abs($feature.scoreInv-100)", expression_type="ARCADE", code_block="", field_type="DOUBLE", enforce_domains="NO_ENFORCE_DOMAINS")
    arcpy.management.CalculateField(in_table=hexgridselection, field="meanCond", expression="(!scoreLCM!+!scoreInvR!)/2", expression_type="PYTHON3", code_block="", field_type="DOUBLE", enforce_domains="NO_ENFORCE_DOMAINS")
    
    # Work on fire departure score
    print("- calculating the fire departure score")
    tmp_FireDep_tif = fr"tmp_{columnValue}_Inv.tif"
    tmp_FireDep_tif = arcpy.sa.ExtractByMask(in_raster=dataFireDep, in_mask_data=nameEVT)
    ZonalSt_Value_FireDep = fr"ZonalSt_{columnValue}_InvRisk"
    arcpy.sa.ZonalStatisticsAsTable(in_zone_data=hexgridselection, zone_field="GRID_ID", in_value_raster=tmp_FireDep_tif,
                                    out_table=ZonalSt_Value_FireDep, ignore_nodata="DATA", statistics_type="MEAN")
    arcpy.management.JoinField(in_data=hexgridselection, in_field="GRID_ID", join_table=ZonalSt_Value_FireDep, join_field="GRID_ID", fields=["MEAN"])[0]
    arcpy.management.CalculateField(in_table=hexgridselection, field="scoreFire", expression="round(!MEAN!,1)", field_type="DOUBLE")
    arcpy.management.DeleteField(hexgridselection, "MEAN")
    #arcpy.management.AlterField(hexgridselection, "MEAN", "scoreLCM", "LCM Score") 

    # apply a layer file
    


    # clean up
    print("- Cleaning up the crumbs")
    arcpy.management.Delete(in_data=[tmp_Value_raster2pt]   )   

