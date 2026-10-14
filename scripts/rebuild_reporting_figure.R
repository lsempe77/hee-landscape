# Rebuild only the abstract-reporting heatmap after its denominator correction.
args <- commandArgs(trailingOnly=TRUE)
root <- normalizePath(if(length(args)) args[[1]] else '.',winslash='/')
lines <- readLines(file.path(root,'scripts/build_remaining_figures_reconciled.R'),warn=FALSE)
a <- grep('^# Growth,',lines)
b <- grep('^# Abstract signals',lines)
c <- grep('^# Frozen intervention',lines)
source(textConnection(c(lines[1:(a-1)],lines[b:(c-1)])))
jsonlite::write_json(manifest,file.path(out,'reporting_figure_manifest.json'),auto_unbox=TRUE,pretty=TRUE)
