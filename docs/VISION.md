# Universal Claude for ArcGIS Pro

## An Open Source AI Integration That Gives Large Language Models Complete Access to the ArcGIS Pro Ecosystem

## Vision

The objective is to create an open-source, community-driven AI integration that enables Large Language Models (LLMs) such as Claude, GPT, Gemini, and locally hosted models to interact with **every publicly accessible capability of ArcGIS Pro**.

This is not intended to be another chatbot that answers GIS questions. Instead, it is a true AI copilot capable of understanding geospatial intent, planning workflows, executing tools, generating code, debugging failures, creating maps, processing imagery, managing enterprise GIS resources, and assisting users from beginner to expert.

The project should become the geospatial equivalent of AI copilots for Blender, Autodesk products, professional CAD software, IDEs, Adobe Creative Cloud, and modern engineering applications.

The architecture must remain model-agnostic, extensible, secure, and fully open source.

---

## Core Mission

Provide AI with complete operational access to ArcGIS Pro through official APIs, automation frameworks, scripting interfaces, SDKs, and extension points while maintaining user control, transparency, auditability, and security.

The AI should be capable of performing every task that a skilled GIS analyst can perform inside ArcGIS Pro.

---

## Scope

The integration should expose every major ArcGIS Pro subsystem.

### ArcPy

Complete support for the entire ArcPy ecosystem: Management, Analysis, Conversion, Cartography, Data Management, Editing, Geometry, Mapping (`arcpy.mp`), Network Analyst, Spatial Analyst, Image Analyst, 3D Analyst, Parcel, Topographic Production, Aviation, GeoAnalytics, Geocoding, Metadata, Server, Sharing, Utility Network, Location Referencing, Workflow Manager, Intelligence, Notebook integration, Data Access (`arcpy.da`), Raster functions, Geoprocessing, environment settings, custom Python Toolboxes (.pyt), toolbox execution/creation/documentation.

The AI should also be capable of: writing, debugging, refactoring and explaining ArcPy code; optimizing performance; converting ModelBuilder models into ArcPy; generating reusable automation scripts; creating Python packages; building complete GIS automation pipelines.

### ArcGIS Pro SDK

Support every public API available through the ArcGIS Pro SDK for .NET: maps, scenes, layouts, graphics, layers, feature/raster layers, annotation, dimension features, editing, selections, bookmarks, tasks, toolboxes, dock panes, custom ribbons, add-ins, geoprocessing, events, project management, metadata, data connections, geodatabases, Utility Networks, Parcel Fabric, Trace Networks, topology, versioning, attribute rules, domains, subtypes, relationship classes, knowledge graphs, CIM manipulation, map automation.

### Geoprocessing

Support every geoprocessing tool available within ArcGIS Pro, including tools provided by installed extensions: analysis (Buffer, Clip, Intersect, Union, Merge, Append, Dissolve, Identity, Near, Spatial Join, Select, Overlay), statistics, raster processing, terrain analysis, hydrology, surface analysis, spatial statistics, network analysis, data conversion, geocoding, linear referencing, georeferencing, projection, data engineering, metadata tools.

Releases should automatically recognize and expose newly installed toolboxes without requiring code changes.

### Mapping and Cartography

Complete automation of: map/scene creation, layouts, legends, scale bars, north arrows, dynamic text, insets, map series, bookmarks, themes, symbology, labeling, annotation, charts, reports, dashboards, atlas production, print layouts, and export to PDF/SVG/image at publication quality.

### Spatial Analysis

Raster algebra, terrain modeling, suitability modeling, hydrology, watershed analysis, viewshed, least-cost path, hot spot analysis, spatial autocorrelation, regression, interpolation, kriging, density analysis, clustering, machine learning, predictive modeling.

### Remote Sensing

Multispectral/hyperspectral imagery, drone imagery, orthomosaics, satellite imagery, image classification, deep learning inference, object detection, change detection, time-series imagery, raster functions, Image Analyst workflows.

### 3D GIS

3D scenes, multipatch, LAS datasets, point clouds, integrated meshes, voxel layers, building scene layers, BIM, terrain, 3D Analyst tools.

### Data Management

File/Enterprise/Mobile geodatabases, SQLite, GeoPackage, shapefiles, CAD, BIM, Excel, CSV, JSON, GeoJSON, KML/KMZ, Parquet, Cloud Raster Formats, NetCDF, HDF, PostgreSQL, SQL Server, Oracle, SAP HANA, Snowflake (where supported).

### Enterprise GIS

ArcGIS Enterprise, ArcGIS Online, portal administration, users/groups/roles, hosted feature layers, map/feature/image/scene/vector-tile services, web maps and scenes, dashboards, Experience Builder, StoryMaps, Hub, Notebooks, Workflow Manager.

### AI Capabilities

Reading projects, inspecting layers, understanding coordinate systems, detecting topology issues, finding broken data sources, repairing paths, optimizing workflows, explaining GIS concepts, teaching ArcGIS Pro, debugging Python and SDK code, suggesting better analysis methods, producing technical documentation, generating metadata, building reproducible workflows, explaining errors in plain language.

### Open Geospatial Ecosystem

GDAL, OGR, PROJ, GeoPandas, Rasterio, Fiona, Shapely, WhiteboxTools, PDAL, PostGIS, PostgreSQL, GeoServer, MapServer, QGIS, Cesium, BlenderGIS, Google Earth Engine, STAC APIs, COGs, PMTiles, OGC API (Features/Tiles/Processes), WMS, WMTS, WFS, WCS, vector tiles, XYZ tiles, MBTiles.

### Open Data Integration

Automatically discover, search, preview, download, validate, and integrate datasets from major free and open data providers: OpenStreetMap, Natural Earth, Sentinel, Landsat, Copernicus, NASA Earthdata, USGS, NOAA, ArcGIS Hub, Statistics Canada, GeoGratis, WorldPop, GBIF, HydroSHEDS, NASA FIRMS, OpenAQ, Humanitarian Data Exchange, CKAN portals, and thousands of national, regional, and municipal open-data portals — understanding licensing, metadata, update frequency, coordinate reference systems, and data quality before recommending or importing data.

---

## Long-Term Goal

The end goal is to create the world's most capable open-source AI-powered geospatial platform — one that can leverage every capability exposed by ArcGIS Pro, ArcPy, the ArcGIS Pro SDK, ArcGIS Enterprise, and the broader open geospatial ecosystem. It should empower analysts, developers, researchers, educators, governments, nonprofits, and businesses to automate, understand, and accelerate geospatial workflows through natural language while remaining transparent, extensible, standards-compliant, and community-driven.
