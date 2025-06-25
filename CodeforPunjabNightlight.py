import ee
ee.Initialize(project='ee-malikiftikhar273')

# Load Punjab 15-min road buffer shapefile
buffer = ee.FeatureCollection("projects/ee-malikiftikhar273/assets/tehsils_punjab")

# ------------------- Loaders -------------------

def get_cropland_image(year):
    if year <= 2020:
        return ee.ImageCollection("MODIS/006/MCD12Q1") \
            .filter(ee.Filter.calendarRange(year, year, 'year')) \
            .first().select('LC_Type1').eq(12).selfMask()
    elif year == 2021:
        return ee.Image("ESA/WorldCover/v200/2021").select('Map').eq(40).selfMask()
    else:  # 2022–2025
        return ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1") \
            .filterDate(f"{year}-01-01", f"{year}-12-31") \
            .select('label').reduce(ee.Reducer.mode()).eq(1).selfMask()

def get_builtup_image(year):
    return ee.Image(f"JRC/GHSL/P2023A/GHS_BUILT_S/{year}").select('built_surface')

def get_nightlight_image(year):
    return ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG") \
        .filterDate(f"{year}-01-01", f"{year}-12-31") \
        .select("avg_rad").mean()

# ------------------- Accumulate All -------------------

def collect_zonal_stats(variable, year_range, loader_func, reducer, scale):
    all_features = []
    for year in year_range:
        print(f"Collecting {variable} for {year}...")
        image = loader_func(year)
        stats = image.reduceRegions(
            collection=buffer,
            reducer=reducer,
            scale=scale(year),
            crs="EPSG:4326"
        ).map(lambda f: f.set({'year': year, 'variable': variable}))
        all_features.append(stats)
    return ee.FeatureCollection(all_features).flatten()

# ------------------- Export Each Combined Table -------------------

# Cropland: 2010–2025
cropland = collect_zonal_stats(
    variable='cropland',
    year_range=list(range(2010, 2026)),
    loader_func=get_cropland_image,
    reducer=ee.Reducer.sum(),
    scale=lambda y: 30 if y >= 2022 or y == 2021 else 500
)

# Built-up: 2000–2025 (specific GHSL years)
builtup_years = [2000, 2005, 2010, 2015, 2020, 2025]
builtup = collect_zonal_stats(
    variable='builtup',
    year_range=builtup_years,
    loader_func=get_builtup_image,
    reducer=ee.Reducer.sum(),
    scale=lambda y: 100
)

# Nightlight: 2010–2025
nightlight = collect_zonal_stats(
    variable='nightlight',
    year_range=list(range(2010, 2026)),
    loader_func=get_nightlight_image,
    reducer=ee.Reducer.mean(),
    scale=lambda y: 500
)
# Export
ee.batch.Export.table.toDrive(
    collection=cropland,
    description='Cropland_Punjab_Buffer_AllYears',
    folder='GEE_exports',
    fileNamePrefix='cropland_punjab_buffer',
    fileFormat='CSV'
).start()

ee.batch.Export.table.toDrive(
    collection=builtup,
    description='Builtup_Punjab_Buffer_AllYears',
    folder='GEE_exports',
    fileNamePrefix='builtup_punjab_buffer',
    fileFormat='CSV'
).start()

ee.batch.Export.table.toDrive(
    collection=nightlight,
    description='Nightlight_Punjab_Buffer_AllYears',
    folder='GEE_exports',
    fileNamePrefix='nightlight_punjab_buffer',
    fileFormat='CSV'
).start()

print("✅ All export tasks started — check your Earth Engine Tasks tab.")

