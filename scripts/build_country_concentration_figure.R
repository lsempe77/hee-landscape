# Run from the repository root:
# Rscript scripts/build_country_concentration_figure.R
# Optional first argument: repository root.
args <- commandArgs(trailingOnly = TRUE)
root <- normalizePath(if (length(args)) args[[1]] else '.', winslash = '/')
source(file.path(root, 'docs', 'theme_hee.R'))
library(patchwork)
out <- file.path(root, 'output', 'figures')
dir.create(out, recursive = TRUE, showWarnings = FALSE)

# Supplied manuscript statistics; no country counts are inferred.
concentration <- data.frame(
  y = 3:1, share = c(49.7, 57.7, 70.7),
  group = c('Top 3 countries', 'Top 5 countries', 'Top 10 countries'),
  countries = c('United States, United Kingdom and China',
                '+ Canada and the Netherlands',
                '+ Australia, Spain, Japan, Germany and Italy'))
write.csv(concentration, file.path(out, 'country_concentration_summary.csv'), row.names = FALSE)
blue <- unname(hee_cat['blue'])
ink <- hee_ink$primary
secondary <- hee_ink$secondary

p_a <- ggplot(concentration, aes(y = y)) +
  geom_segment(aes(x = 0, xend = 100, yend = y), colour = hee_ink$grid, linewidth = 6) +
  geom_segment(aes(x = 0, xend = share, yend = y), colour = blue, linewidth = 6) +
  geom_text(aes(x = 0, y = y + .23, label = group), hjust = 0, size = 4, fontface = 'bold') +
  geom_text(aes(x = share + 2, label = sprintf('%.1f%%', share)), hjust = 0, size = 4, fontface = 'bold') +
  geom_text(aes(x = 0, y = y - .25, label = countries), hjust = 0, size = 3.3, colour = secondary) +
  scale_x_continuous(limits = c(0, 100), breaks = seq(0, 100, 25), labels = function(x) paste0(x, '%'), expand = c(0, 0)) +
  scale_y_continuous(limits = c(.5, 3.55), breaks = NULL) +
  labs(title = 'A  Study concentration', x = 'Share of studies that name a country', y = NULL) +
  theme_hee(12, grid = 'none')

coverage <- data.frame(y = c(3, 2, 1), value = c('187 / 204', '98.7%', '71.9%'),
  detail = c('countries or territories represented',
             'of geographies with >1 million people\nhad at least one evaluation',
             'of evaluations named\none or more countries'))
p_b <- ggplot(coverage, aes(x = 0, y = y)) +
  geom_text(aes(label = value), hjust = 0, size = 9, fontface = 'bold', colour = blue) +
  geom_text(aes(y = y - .35, label = detail), hjust = 0, size = 3.5, colour = secondary, lineheight = 1.15) +
  xlim(0, 1) + ylim(.35, 3.55) + labs(title = 'B  Geographic coverage') +
  theme_hee(12, grid = 'none') + theme(axis.text = element_blank(), axis.title = element_blank())

income <- data.frame(y = c(2, 1), value = c(6.4, 84.1),
                     label = c('Low-income countries', 'High-income countries'))
p_c <- ggplot(income, aes(y = y)) +
  geom_segment(aes(x = 0, xend = value, yend = y), linewidth = 6, colour = blue) +
  geom_text(aes(x = 0, y = y + .3, label = label), hjust = 0, size = 3.5, colour = secondary) +
  geom_text(aes(x = value + 2, label = sprintf('%.1f', value)), hjust = 0, size = 4, fontface = 'bold') +
  scale_x_continuous(limits = c(0, 100), breaks = c(0, 25, 50, 75, 100), expand = c(0, 0)) +
  scale_y_continuous(limits = c(.55, 2.65), breaks = NULL) +
  labs(title = 'C  Evidence relative to population', x = 'Median evaluations per 10 million people', y = NULL) +
  theme_hee(12, grid = 'none')

metrics <- data.frame(y = c(2, 1), value = c('13.1 times', '0.84'),
  detail = c('higher median in high-income countries', 'Gini coefficient of country-level study counts'))
p_d <- ggplot(metrics, aes(x = 0, y = y)) +
  geom_text(aes(label = value), hjust = 0, size = 8, fontface = 'bold', colour = blue) +
  geom_text(aes(y = y - .34, label = detail), hjust = 0, size = 3.4, colour = secondary) +
  xlim(0, 1) + ylim(.5, 2.65) + labs(title = 'D  Inequality in evidence') +
  theme_hee(12, grid = 'none') + theme(axis.text = element_blank(), axis.title = element_blank())

caption <- paste0(
  'Country groups in A are cumulative. Multi-country studies are counted once within each group. ',
  'C includes countries with >1 million people; the ratio in D is calculated from the reported medians.<br>',
  'Gini counts studies once per country among represented countries; including countries with no studies gives 0.842. ',
  'Eritrea and Mauritius are the coverage exceptions among geographies with >1 million people.<br>',
  'Source: supplied manuscript summary statistics.')
figure <- ((p_a | p_b) / (p_c | p_d)) +
  plot_layout(widths = c(1.5, 1), heights = c(1.6, 1)) +
  plot_annotation(title = 'Health economic evidence is concentrated in a few countries',
                  caption = caption, theme = theme_hee(13, grid = 'none'))
for (ext in c('png', 'pdf', 'svg')) {
  ggsave(file.path(out, paste0('health_economic_evidence_concentration_hee.', ext)),
         figure, width = 13, height = 8.5, dpi = 300, bg = 'white')
}
