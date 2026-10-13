# Export source geography and national GBD rows for the denominator audit.
# Run from the repository root; outputs stay in the ignored raw-data directory.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 1)
root <- args[[1]]
stopifnot(requireNamespace("countrycode", quietly = TRUE),
          requireNamespace("rnaturalearth", quietly = TRUE),
          requireNamespace("sf", quietly = TRUE))
gbd <- read.csv(file.path(root, "data/gbd2023_dalys_country_total.csv"))
gbd <- subset(gbd, metric_name == "Number" & age_name == "All ages" &
              sex_name == "Both" & cause_name == "All causes" & year == 2023)
gbd$iso3 <- countrycode::countrycode(gbd$location_name, "country.name", "iso3c", warn = FALSE)
gbd$iso3[gbd$location_id == 155] <- "TUR"
gbd$iso3[gbd$location_name == "Taiwan (Province of China)"] <- "TWN"
stopifnot(!anyNA(gbd$iso3), !anyDuplicated(gbd$iso3))
write.csv(gbd, "data/raw/denominator_gbd_source.csv", row.names = FALSE)
ne <- sf::st_drop_geometry(rnaturalearth::ne_countries(scale = "medium", returnclass = "sf"))
write.csv(ne[, c("iso_a3_eh", "admin", "type")],
          "data/raw/denominator_geography_source.csv", row.names = FALSE)
