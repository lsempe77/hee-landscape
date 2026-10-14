for (p in c('dplyr','ggplot2','sf','rnaturalearth','rnaturalearthdata','ragg','readr','ggrepel','patchwork','jsonlite')) cat(p,requireNamespace(p,quietly=TRUE),'\n')
