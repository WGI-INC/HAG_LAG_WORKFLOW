import arcpy
import os


class Toolbox:
    def __init__(self):
        self.label = "Building Elevation Tools"
        self.alias = "BuildingElevationTools"
        self.tools = [BuildingElevationExtractor]


class BuildingElevationExtractor:

    def __init__(self):
        self.label = "Extract Building Elevations"
        self.description = (
            "Calculates HAG (Highest Adjacent Grade), LAG (Lowest Adjacent Grade), "
            "and Building_Height for building footprint polygons using a DEM raster "
            "and a classified LiDAR dataset (Class 6 - Building points)."
        )
        self.canRunInBackground = False

    # ------------------------------------------------------------------
    # Define tool parameters
    # ------------------------------------------------------------------
    def getParameterInfo(self):

        param_features = arcpy.Parameter(
            displayName="Building Footprints (Feature Class)",
            name="in_features",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        param_raster = arcpy.Parameter(
            displayName="Input DEM Raster",
            name="in_raster",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input"
        )

        param_las = arcpy.Parameter(
            displayName="Input LAS Dataset (.lasd)",
            name="in_las_dataset",
            datatype="DELasDataset",
            parameterType="Required",
            direction="Input"
        )

        param_cell_size = arcpy.Parameter(
            displayName="LiDAR Raster Cell Size (meters)",
            name="cell_size",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param_cell_size.value = 1.0

        param_lidar_units = arcpy.Parameter(
            displayName="LiDAR Vertical Units",
            name="lidar_units",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        param_lidar_units.filter.type = "ValueList"
        param_lidar_units.filter.list = ["Meters", "Feet"]
        param_lidar_units.value = "Meters"

        param_cleanup = arcpy.Parameter(
            displayName="Delete Temporary Rasters and Tables",
            name="cleanup",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        param_cleanup.value = True

        return [
            param_features,
            param_raster,
            param_las,
            param_cell_size,
            param_lidar_units,
            param_cleanup
        ]

    def isLicensed(self):
        """Requires Spatial Analyst extension."""
        try:
            if arcpy.CheckExtension("Spatial") == "Available":
                return True
        except Exception:
            pass
        return False

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        """Validate inputs and warn user about potential issues."""
        features = parameters[0]
        if features.value and not features.hasBeenValidated:
            desc = arcpy.Describe(features.valueAsText)
            if desc.shapeType != "Polygon":
                features.setErrorMessage("Input feature class must be a Polygon layer.")

        cell_size = parameters[3]
        if cell_size.value and cell_size.value <= 0:
            cell_size.setErrorMessage("Cell size must be a positive number.")

        return

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------
    def execute(self, parameters, messages):

        in_features   = parameters[0].valueAsText
        in_raster     = parameters[1].valueAsText
        las_dataset   = parameters[2].valueAsText
        cell_size     = parameters[3].value if parameters[3].value else 1.0
        lidar_units   = parameters[4].valueAsText
        do_cleanup    = parameters[5].value

        arcpy.env.overwriteOutput = True
        arcpy.CheckOutExtension("Spatial")

        gdb_path = os.path.dirname(in_features)

        # Conversion factor: LiDAR Z_RANGE is in meters or feet → output feet
        unit_factor = 3.28084 if lidar_units == "Meters" else 1.0

        # ── STEP 1: Ensure output fields exist ────────────────────────────────
        messages.addMessage("=" * 60)
        messages.addMessage("Step 1 of 5: Checking / creating output fields...")
        existing_fields = [f.name for f in arcpy.ListFields(in_features)]

        for field in ["HAG", "LAG"]:
            if field not in existing_fields:
                arcpy.management.AddField(in_features, field, "FLOAT")
                messages.addMessage(f"  + Created field: {field}")
            else:
                messages.addMessage(f"  ✓ Field already exists: {field}")

        if "Building_Height" not in existing_fields:
            arcpy.management.AddField(in_features, "Building_Height", "DOUBLE")
            messages.addMessage("  + Created field: Building_Height")
        else:
            messages.addMessage("  ✓ Field already exists: Building_Height")

        # ── STEP 2: DEM Zonal Statistics → HAG / LAG ──────────────────────────
        messages.addMessage("-" * 60)
        messages.addMessage("Step 2 of 5: Running DEM zonal statistics (MIN/MAX)...")
        dem_table = os.path.join(gdb_path, "tmp_zonal_dem")

        try:
            arcpy.sa.ZonalStatisticsAsTable(
                in_zone_data=in_features,
                zone_field="OBJECTID",
                in_value_raster=in_raster,
                out_table=dem_table,
                ignore_nodata="DATA",
                statistics_type="MIN_MAX"
            )
            messages.addMessage(f"  ✓ DEM zonal stats table written to: {dem_table}")
        except Exception as e:
            messages.addErrorMessage(f"  ✗ ZonalStatisticsAsTable (DEM) failed: {e}")
            raise

        zone_stats = {}
        with arcpy.da.SearchCursor(dem_table, ["OBJECTID", "MIN", "MAX"]) as cursor:
            for row in cursor:
                zone_stats[row[0]] = {
                    "LAG": round(row[1], 3) if row[1] is not None else None,
                    "HAG": round(row[2], 3) if row[2] is not None else None
                }
        messages.addMessage(f"  ✓ Loaded DEM stats for {len(zone_stats)} features.")

        # ── STEP 3: LiDAR Z_RANGE raster ──────────────────────────────────────
        messages.addMessage("-" * 60)
        messages.addMessage("Step 3 of 5: Creating Z_RANGE raster from LiDAR Class 6...")
        zrange_raster = os.path.join(gdb_path, "tmp_zrange_raster")

        try:
            arcpy.management.MakeLasDatasetLayer(
                in_las_dataset=las_dataset,
                out_layer="las_class6_layer",
                class_code="6"
            )
            arcpy.management.LasPointStatsAsRaster(
                in_las_dataset="las_class6_layer",
                out_raster=zrange_raster,
                method="Z_RANGE",
                sampling_type="CELLSIZE",
                sampling_value=cell_size
            )
            messages.addMessage(f"  ✓ Z_RANGE raster written to: {zrange_raster}")
        except Exception as e:
            messages.addErrorMessage(f"  ✗ LiDAR raster creation failed: {e}")
            raise

        # ── STEP 4: LiDAR Zonal Statistics → Building_Height ──────────────────
        messages.addMessage("-" * 60)
        messages.addMessage("Step 4 of 5: Running LiDAR zonal statistics (MAX Z_RANGE)...")
        lidar_table = os.path.join(gdb_path, "tmp_zonal_lidar")

        try:
            arcpy.sa.ZonalStatisticsAsTable(
                in_zone_data=in_features,
                zone_field="OBJECTID",
                in_value_raster=zrange_raster,
                out_table=lidar_table,
                ignore_nodata="DATA",
                statistics_type="MAX"
            )
            messages.addMessage(f"  ✓ LiDAR zonal stats table written to: {lidar_table}")
        except Exception as e:
            messages.addErrorMessage(f"  ✗ ZonalStatisticsAsTable (LiDAR) failed: {e}")
            raise

        height_stats = {}
        with arcpy.da.SearchCursor(lidar_table, ["OBJECTID", "MAX"]) as cursor:
            for row in cursor:
                height_stats[row[0]] = (
                    round(row[1] * unit_factor, 3) if row[1] is not None else None
                )
        messages.addMessage(f"  ✓ Loaded LiDAR height stats for {len(height_stats)} features.")

        # ── STEP 5: Write all attributes in a single cursor pass ───────────────
        messages.addMessage("-" * 60)
        messages.addMessage("Step 5 of 5: Writing HAG, LAG, and Building_Height...")
        updated = 0
        skipped = 0
        fields = ["OBJECTID", "HAG", "LAG", "Building_Height"]

        with arcpy.da.UpdateCursor(in_features, fields) as cursor:
            for row in cursor:
                oid  = row[0]
                dem  = zone_stats.get(oid, {})
                bh   = height_stats.get(oid)

                row[1] = dem.get("HAG")
                row[2] = dem.get("LAG")
                row[3] = bh
                cursor.updateRow(row)

                if dem or bh is not None:
                    updated += 1
                else:
                    skipped += 1

        messages.addMessage(f"  ✓ Features updated : {updated}")
        if skipped:
            messages.addWarningMessage(
                f"  ⚠ Features with no matching stats (NoData zones): {skipped}"
            )

        # ── STEP 6: Optional cleanup ───────────────────────────────────────────
        if do_cleanup:
            messages.addMessage("-" * 60)
            messages.addMessage("Cleaning up temporary datasets...")
            for item in ["las_class6_layer", dem_table, lidar_table, zrange_raster]:
                try:
                    arcpy.management.Delete(item)
                    messages.addMessage(f"  - Deleted: {item}")
                except Exception as e:
                    messages.addWarningMessage(f"  - Could not delete {item}: {e}")
        else:
            messages.addMessage(
                "Cleanup skipped. Temporary datasets retained in GDB for inspection."
            )

        messages.addMessage("=" * 60)
        messages.addMessage(
            "SUCCESS — HAG, LAG, and Building_Height updated "
            f"for {updated} building footprints."
        )

    def postExecute(self, parameters):
        return
