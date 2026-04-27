# Building Elevation Tools — ArcGIS Pro Python Toolbox

A Python Toolbox (`.pyt`) for ArcGIS Pro that extracts **HAG**, **LAG**, and **Building Height** attributes for building footprint polygons using a DEM raster and a classified LiDAR dataset.

---

## Overview

This toolbox consolidates two separate elevation extraction workflows into a single geoprocessing tool:

- **HAG (Highest Adjacent Grade)** — maximum ground elevation beneath each building footprint, derived from a DEM
- **LAG (Lowest Adjacent Grade)** — minimum ground elevation beneath each building footprint, derived from a DEM
- **Building_Height** — vertical extent of the building in feet, derived from LiDAR Class 6 (Building) points

Typical use cases include flood risk assessment, insurance underwriting, 3D building modeling, and site elevation reporting.

---

## Requirements

| Requirement | Details |
|---|---|
| ArcGIS Pro | 2.x or later |
| Python | 3.x (bundled with ArcGIS Pro) |
| Spatial Analyst Extension | Required (tool validates on open) |
| LiDAR Classification | LAS dataset must have Class 6 (Building) points classified |

---

## Inputs

| Parameter | Type | Description |
|---|---|---|
| Building Footprints | Polygon Feature Class | The building footprints to be attributed |
| Input DEM Raster | Raster Dataset | Ground elevation surface for HAG/LAG extraction |
| Input LAS Dataset | LAS Dataset (.lasd) | Point cloud filtered to Class 6 for height extraction |
| Cell Size (meters) | Double | Resolution of the Z_RANGE raster (default: 1.0m) |
| LiDAR Vertical Units | Meters / Feet | Controls unit conversion for Building_Height output |
| Delete Temporary Data | Boolean | Removes intermediate rasters and tables after completion |

---

## Outputs

All outputs are written directly to the input feature class as new (or updated) fields:

| Field | Type | Description |
|---|---|---|
| `LAG` | Float | Minimum DEM elevation under the footprint (3 decimal places) |
| `HAG` | Float | Maximum DEM elevation under the footprint (3 decimal places) |
| `Building_Height` | Double | Max Z_RANGE of LiDAR Class 6 points, converted to feet (3 decimal places) |

---

## How It Works

```
DEM Raster ──────────────────┐
                              ├──► ZonalStatisticsAsTable (MIN/MAX) ──► HAG, LAG
Building Footprints ─────────┤
                              ├──► ZonalStatisticsAsTable (MAX) ──────► Building_Height
LiDAR (.lasd) Class 6 ───────┘
         │
         └──► LasPointStatsAsRaster (Z_RANGE, 1m cell)
```

1. Checks for and creates `HAG`, `LAG`, and `Building_Height` fields if missing
2. Runs `ZonalStatisticsAsTable` on the DEM to get MIN/MAX elevation per footprint
3. Filters LiDAR to Class 6, generates a Z_RANGE raster at the specified cell size
4. Runs `ZonalStatisticsAsTable` on the Z_RANGE raster to get MAX vertical spread per footprint
5. Writes all three values back to the feature class in a single cursor pass
6. Optionally deletes all temporary rasters and tables

---

## Usage

1. Clone or download this repository
2. In ArcGIS Pro, open the **Catalog** pane
3. Right-click a folder connection → **Add Toolbox** → select `BuildingElevationTools.pyt`
4. Expand the toolbox and double-click **Extract Building Elevations**
5. Fill in the parameters and click **Run**

---

## Notes

- If the LiDAR dataset is in **feet vertically** (common in older US datasets), set *LiDAR Vertical Units* to `Feet` to skip the metre-to-feet conversion
- Class 6 filtering only works if the point cloud has been properly classified — unclassified datasets will produce empty or NoData results
- Features that fall entirely in NoData zones will receive `null` values and are reported as a warning in the tool output
- The tool uses `OBJECTID` as the join key between zonal stats and the feature class — avoid datasets where OBJECTIDs may be reassigned between operations

---

## File Structure

```
BuildingElevationTools/
│
├── BuildingElevationTools.pyt   # Main Python Toolbox
└── README.md                    # This file
```

---

## Background

This toolbox was built by consolidating three standalone scripts that were previously run separately:

- `Script 1 / 3` — DEM-based HAG/LAG extraction via `ZonalStatisticsAsTable`
- `Script 2` — LiDAR Class 6 Z_RANGE raster → Building Height in feet

The combined toolbox runs both workflows in sequence and writes all outputs in a single update pass, with validation, progress messaging, and optional cleanup built in.
