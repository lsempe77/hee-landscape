# Rebuild residual static figures directly from the reconciled CSVs.
# Frozen topic coordinates are filtered, never refitted. No upstream files are modified.
suppressPackageStartupMessages({library(dplyr);library(tidyr);library(readr);library(ggplot2);library(scales);library(sf);library(rnaturalearth);library(jsonlite);library(patchwork)})
args <- commandArgs(trailingOnly=TRUE)
root <- normalizePath(if(length(args)) args[[1]] else '.',winslash='/')
raw <- file.path(root,'data/raw'); out <- file.path(root,'exports/publication_reconciliation/figure_refresh')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
rd <- function(file) read_csv(file.path(raw,file),col_types=cols(.default='c'),show_col_types=FALSE,na=c('','NA'))
m <- rd('hee_analysis_master_v2_1.csv') |> filter(is_eligible=='TRUE') |>
  mutate(year=as.integer(year),model=model_based=='TRUE',oa=as.numeric(is_oa),qaly=uses_qaly=='TRUE')
stopifnot(nrow(m)==41610L,!anyDuplicated(m$record_id))
geo <- rd('hee_geo_long_v2_1.csv') |> filter(record_id %in% m$record_id,is_special=='FALSE',!is.na(iso3)) |> distinct(record_id,iso3,.keep_all=TRUE)
stopifnot(!'132018093' %in% geo$record_id)
countries <- as_tibble(fromJSON(file.path(root,'docs/data/countries.json'))) |> select(-income_y)
cnt <- geo |> count(iso3,name='studies_full')
countries <- countries |> left_join(cnt,by='iso3') |> mutate(studies_full=coalesce(studies_full,0L))
stopifnot(all(countries$studies==countries$studies_full))
burden <- rd('denominator_gbd_source.csv') |> transmute(iso3,dalys=as.numeric(val))
stopifnot(nrow(burden)==204L,!anyDuplicated(burden$iso3))
outcomes <- rd('hee_outcomes_long.csv'); daly <- unique(outcomes$record_id[outcomes$family=='DALYs'])
m <- m |> mutate(generic=qaly|record_id %in% daly)
ext <- rd('hee_intervention_class.csv') |> select(record_id,intervention_class)
m <- m |> left_join(ext,by='record_id')
stopifnot(nrow(m)==41610L)
groups <- c('Low income','Lower middle income','Upper middle income','High income')
palette <- setNames(c('#D98F7A','#D6B264','#62A89B','#6D91BE'),groups)
bg <- '#FAF9F7'; ink <- '#10243e'
theme_set(theme_minimal(base_family='Arial',base_size=11)+theme(plot.background=element_rect(fill=bg,colour=NA),panel.background=element_rect(fill=bg,colour=NA),plot.title=element_text(face='bold',size=18,colour=ink),plot.subtitle=element_text(size=11,colour='#5a564d'),plot.caption=element_text(size=9,hjust=0,lineheight=1.2),panel.grid.minor=element_blank(),plot.margin=margin(16,18,16,18),legend.position='bottom'))
manifest <- list()
wrap <- function(s,width=125) paste(strwrap(s,width=width),collapse='\n')
save <- function(p,old,title,caption,width=10,height=7,summary=NULL){
  stem <- paste0(sub('\\.(webp|svg)$','',old),'_reconciled')
  if(inherits(p,'patchwork')) p <- p+plot_annotation(title=title,caption=wrap(caption),theme=theme(plot.title=element_text(face='bold',size=18),plot.caption=element_text(size=9,hjust=0))) else p <- p+labs(title=title,caption=wrap(caption))
  ggsave(file.path(out,paste0(stem,'.png')),p,width=width,height=height,dpi=170,bg=bg,device=ragg::agg_png,limitsize=FALSE)
  manifest[[old]] <<- list(file=paste0(stem,'.webp'),title=title,caption=caption,summary=if(is.null(summary)) title else summary,builder='scripts/build_remaining_figures_reconciled.R',eligible_count=nrow(m))
  cat(old,'rebuilt\n')
}
single <- m |> filter(geo_scope=='single_country',income_group_pubyear %in% groups) |> mutate(income=factor(income_group_pubyear,levels=groups),side=if_else(income_group_pubyear=='High income','High-income settings','Low- and middle-income settings'))
base_note <- 'Eligible records published 2010-2026; 2026 is partial. Country counts use unique study-country pairs, so multi-country studies count once for each named country.'
income_note <- 'Study-level income groups use the World Bank classification in force on 1 January of publication year. Country-level colours use July 2026 groups.'

# Growth, including the explicitly partial final year.
byyr <- m |> count(year) |> arrange(year) |> mutate(cumulative=cumsum(n))
reference <- byyr |> mutate(reference=first(cumulative)+mean(n[year %in% 2010:2012])*(year-2010))
p <- ggplot(byyr,aes(year,cumulative))+geom_area(fill='#62A89B',alpha=.18)+geom_line(colour='#326a70',linewidth=1)+geom_line(data=reference,aes(y=reference),linetype=2,colour='#999')+geom_point(data=filter(byyr,year==2026),size=3)+scale_y_continuous(labels=comma)+scale_x_continuous(breaks=seq(2010,2026,2))+labs(x='Publication year',y='Cumulative included records',subtitle='The final-year point is partial; the dashed line keeps annual output at its 2010-2012 rate.')
save(p,'fig_growth.webp','Growth of the economic-evaluation evidence base',paste('Base: 41,610 included records.',base_note,'The reference is descriptive, not a forecast.'))

# Generic outcome reporting by model status.
generic <- m |> filter(!is.na(model)) |> group_by(model) |> summarise(n=n(),k=sum(generic),.groups='drop') |> mutate(label=if_else(model,'Model-based','Not model-based'),pct=100*k/n)
p <- ggplot(generic,aes(label,pct,fill=label))+geom_col(width=.55)+geom_text(aes(label=paste0(round(pct,1),'%\n(n=',comma(n),')')),vjust=-.3)+scale_fill_manual(values=c('#6D91BE','#D98F7A'),guide='none')+scale_y_continuous(limits=c(0,100),labels=function(x)paste0(x,'%'))+labs(x=NULL,y='Records reporting QALYs or DALYs')
save(p,'paper02.webp','Generic outcome reporting differs by model use',paste('Base:',comma(sum(generic$n)),'included records with a model-use flag. Generic outcomes are QALYs or DALYs; a record reporting both counts once. Abstract reporting does not establish methodological quality.'))

# Abstract signals by intervention class.
class_lab <- c(pharma='Pharmaceuticals',vaccine='Vaccines',screening_diagnostic='Screening & diagnosis',surgical_procedural='Surgery & procedures',device_or_supply='Devices & supplies',behavioural_preventive='Behavioural & preventive',care_model_organisational='Care models & organisation',financing_payment_policy='Financing & payment policy',other='Other')
sig <- c(has_icer='Reports an ICER',has_threshold='States a threshold',has_uncertainty='Reports uncertainty',has_perspective='States a perspective',model='Model-based')
signals <- m |> mutate(across(c(has_icer,has_threshold,has_uncertainty,has_perspective),~as.numeric(.x)))
signal_groups <- signals |> filter(intervention_class %in% setdiff(names(class_lab),'other')) |> mutate(class=unname(class_lab[intervention_class]))
signal_groups <- bind_rows(signal_groups,signals |> mutate(class='All included records'))
rates <- signal_groups |> group_by(class) |> summarise(n=n(),across(all_of(names(sig)),~100*sum(.x,na.rm=TRUE)/n()),.groups='drop') |> pivot_longer(all_of(names(sig)),names_to='signal',values_to='pct') |> mutate(signal=factor(unname(sig[signal]),levels=unname(sig)))
p <- ggplot(rates,aes(signal,class,fill=pct))+geom_tile(colour=bg,linewidth=1)+geom_text(aes(label=sprintf('%.1f%%',pct)),size=3)+scale_fill_gradient(low='#edf1f2',high='#62A89B',name='Share (%)')+labs(x=NULL,y=NULL)+theme(axis.text.x=element_text(angle=20,hjust=1),panel.grid=element_blank())
save(p,'fig_intervention_decision.webp','What abstracts report for healthcare decisions',paste('Base: 41,610 included records; intervention rows use the included records within each class. Primary intervention class only; residual Other omitted. All columns use the full row denominator, including records with an unavailable flag; model-based is the share positively identified as model-based. Signals are abstract keyword flags, not a full-text quality assessment. "Not reported" does not mean "not done".'),11,8)

# Frozen intervention topic map, filtered to eligible records.
pts <- rd('topic_map.csv') |> filter(record_id %in% m$record_id) |> mutate(x=as.numeric(x),y=as.numeric(y),cluster=as.integer(cluster)) |> left_join(m |> select(record_id,intervention_class),by='record_id')
stopifnot(nrow(pts)==41583L)
class_rates <- single |> filter(!is.na(intervention_class)) |> group_by(intervention_class) |> summarise(n=n(),lmic=100*mean(side=='Low- and middle-income settings'),.groups='drop')
pts <- pts |> left_join(class_rates,by='intervention_class') |> mutate(class=if_else(cluster==-1,NA_character_,unname(class_lab[intervention_class])))
cent <- pts |> filter(!is.na(class)) |> group_by(class) |> summarise(x=median(x),y=median(y),lmic=first(lmic),.groups='drop') |> mutate(label=paste0(class,'\n',round(lmic),'% LMIC'))
classes <- setNames(c('#6D91BE','#D98F7A','#9B87B8','#b23a48','#D6B264','#62A89B','#16a085','#a0522d','#888'),unname(class_lab))
legend_labels <- setNames(paste0(unname(class_lab[class_rates$intervention_class]),' (',round(class_rates$lmic),'% LMIC)'),unname(class_lab[class_rates$intervention_class]))
pa <- ggplot(pts,aes(x,y))+geom_point(aes(colour=class),size=.35,alpha=.65)+scale_colour_manual(values=classes,na.value='#ddd',na.translate=FALSE,name='Primary intervention',labels=function(x) unname(legend_labels[x]))+coord_equal()+theme_void()+theme(legend.position='bottom')+labs(title='A | Primary intervention')
pb <- ggplot(pts,aes(x,y))+geom_point(aes(colour=if_else(cluster==-1,NA_real_,lmic)),size=.35,alpha=.65)+scale_colour_gradient(low='#6D91BE',high='#D98F7A',limits=c(0,100),na.value='#ddd',name='LMIC share (%)')+coord_equal()+theme_void()+labs(title='B | Share of each intervention class in LMIC settings')
save(pa+pb+plot_layout(guides='collect'),'fig_intervention_map.webp','What kinds of healthcare does the research cover?',paste('Base:',comma(nrow(pts)),'eligible records with frozen topic coordinates; 27 included records have no coordinates. Grey points are HDBSCAN noise or missing intervention labels. LMIC shares are computed among',comma(nrow(single)),'single-country records with known publication-year income, by primary intervention class. Coordinates were filtered, not refitted.',income_note),15,9)

# Open access, a common base for all three series.
oa <- single |> filter(year<=2025,oa %in% c(0,1))
oa_by <- oa |> group_by(year,side) |> summarise(n=n(),pct=100*mean(oa),.groups='drop')
oa_all <- oa |> group_by(year) |> summarise(n=n(),pct=100*mean(oa),.groups='drop') |> mutate(side='All settings in this comparison')
p <- ggplot(bind_rows(oa_by,oa_all),aes(year,pct,colour=side))+geom_line(linewidth=1)+geom_point(size=1.5)+scale_colour_manual(values=c('High-income settings'='#6D91BE','Low- and middle-income settings'='#D98F7A','All settings in this comparison'='#555'))+scale_y_continuous(limits=c(0,100),labels=function(x)paste0(x,'%'))+scale_x_continuous(breaks=seq(2010,2025,3))+labs(x='Publication year',y='Open-access share',colour=NULL)
save(p,'fig_openaccess.webp','How access to economic evidence has changed',paste('Base:',comma(nrow(oa)),'single-country included records, 2010-2025, with known publication-year income and known open-access status. All three lines use this same base; 2026 is excluded as partial.',income_note),11,7)

# Country density and burden plots use the checked country universe.
country_base <- countries |> mutate(income=factor(income,levels=groups),per10m=studies/pop*1e7,per100k=studies/dalys*1e5)
pop_base <- country_base |> filter(studies>0,!is.na(pop),pop>0,!is.na(income))
med <- pop_base |> group_by(income) |> summarise(value=median(per10m),.groups='drop')
p <- ggplot(pop_base,aes(income,per10m,colour=income))+geom_point(aes(size=pop),position=position_jitter(width=.18,height=0,seed=42),alpha=.7)+geom_errorbar(data=med,inherit.aes=FALSE,mapping=aes(x=income,y=value,ymin=value,ymax=value),width=.65,linetype=2)+scale_y_log10(labels=comma)+scale_colour_manual(values=palette,guide='none')+scale_size_area(max_size=14,name='Population')+labs(x=NULL,y='Studies per 10 million people (log scale)')
save(p,'paper03.webp','Research availability relative to population',paste('Base:',nrow(pop_base),'countries with at least one study, population and income classification from the',nrow(countries),'country website list. Zero-study countries are omitted from the log axis. Dashed lines are within-group medians.',base_note,income_note),11,8)
burden_base <- country_base |> filter(studies>0,!is.na(dalys),dalys>0,!is.na(income))
p <- ggplot(burden_base,aes(dalys,per100k,colour=income,size=pop))+geom_point(alpha=.75)+scale_x_log10(labels=label_number(scale_cut=cut_short_scale()))+scale_y_log10(labels=label_number())+scale_colour_manual(values=palette,name='Income group')+scale_size_area(max_size=14,name='Population')+labs(x='Disease burden: DALYs (log scale)',y='Studies per 100,000 DALYs (log scale)')
save(p,'paper07.webp','Research intensity relative to disease burden',paste('Base:',nrow(burden_base),'countries with studies and non-missing GBD 2023 all-cause DALYs and income classification. Countries with zero studies are omitted from the log scale.',base_note,income_note),11,8)
pair_total <- sum(burden_base$studies);burden_total <- sum(filter(country_base,!is.na(dalys))$dalys)
expected <- filter(country_base,!is.na(dalys)) |> mutate(expected=sum(studies)*dalys/sum(dalys))
p <- ggplot(burden_base,aes(dalys,studies,colour=income,size=pop))+geom_point(alpha=.75)+geom_abline(intercept=log10(sum(expected$studies)/sum(expected$dalys)),slope=1,linetype=2,colour='#555')+scale_x_log10(labels=label_number(scale_cut=cut_short_scale()))+scale_y_log10(labels=comma)+scale_colour_manual(values=palette,name='Income group')+scale_size_area(max_size=14,name='Population')+labs(x='Disease burden: DALYs (log scale)',y='Study-country counts (log scale)')
save(p,'fig_injustice.webp','How research attention compares with disease burden',paste('Base:',nrow(burden_base),'countries plotted;',nrow(expected),'countries contribute to the burden-proportional reference, including zero-study countries.',comma(sum(expected$studies)),'study-country pairs. Dashed line: the pair total multiplied by the burden share of each country. Proportionality is a reference point, not an adequacy target.',base_note),11,8)

# Local capacity: actual known author locations, not study-country proxies.
aff <- rd('hee_affiliation_countries_v2.csv') |> filter(record_id %in% m$record_id) |> select(record_id,affiliation_countries)
local_base <- single |> select(record_id,country_iso3) |> inner_join(aff,by='record_id') |> filter(!is.na(affiliation_countries)) |> mutate(iso2=countrycode::countrycode(country_iso3,'iso3c','iso2c',warn=FALSE),local=mapply(function(a,b) !is.na(b) && b %in% strsplit(a,';',fixed=TRUE)[[1]],affiliation_countries,iso2))
local <- local_base |> group_by(iso3=country_iso3) |> summarise(n=n(),pct=100*mean(local),.groups='drop') |> filter(n>=5) |> inner_join(country_base |> select(iso3,country,income,dalys),by='iso3') |> filter(!is.na(dalys),!is.na(income))
p <- ggplot(local,aes(pct,dalys,colour=income,size=n))+geom_point(alpha=.8)+scale_y_log10(labels=label_number(scale_cut=cut_short_scale()))+scale_x_continuous(limits=c(0,100),labels=function(x)paste0(x,'%'))+scale_colour_manual(values=palette,name='Income group')+scale_size_area(max_size=15,name='Studies with author locations')+labs(x='Studies with at least one locally based author',y='Disease burden: DALYs (log scale)')
save(p,'fig_funder_capacity.webp','Local authorship and potential research-capacity gaps',paste('Base:',nrow(local),'countries with at least five single-country studies with known author locations, publication-year income, and a GBD 2023 burden value. Local authorship means an affiliation in the country studied; it is a proxy, not a full measure of capacity. Point area is the number of studies with known author locations.',income_note),11,8)

# Regional model-use comparison, retaining the pair denominator.
pairs <- geo |> select(record_id,iso3,un_region) |> left_join(m |> select(record_id,model),by='record_id') |> filter(!is.na(model))
global_model <- 100*mean(pairs$model)
reg <- pairs |> filter(!is.na(un_region)) |> group_by(un_region) |> summarise(n=n(),pct=100*mean(model),.groups='drop') |> filter(n>=100) |> arrange(pct) |> mutate(un_region=factor(un_region,levels=un_region))
p <- ggplot(reg,aes(pct,un_region))+geom_col(fill='#6D91BE')+geom_vline(xintercept=global_model,linetype=2)+geom_text(aes(label=sprintf('%.1f%% (n=%s)',pct,comma(n))),hjust=-.08,size=3)+scale_x_continuous(limits=c(0,100),labels=function(x)paste0(x,'%'))+labs(x='Model-based share',y=NULL)
save(p,'fig_map_model.webp','Model use across study regions',paste('Base:',comma(nrow(pairs)),'unique study-country pairs with known model status. Regions with at least 100 pairs are shown. Dashed reference:',round(global_model,1),'%, calculated across all pairs, so this differs from the study-level Overview share.',base_note),11,8)

# Projected maps rebuilt from Natural Earth shapes and current counts.
world <- ne_countries(scale='medium',returnclass='sf') |> filter(admin!='Antarctica') |> mutate(iso3=iso_a3_eh) |> st_transform('+proj=robin')
map_theme <- theme_void()+theme(plot.background=element_rect(fill=bg,colour=NA),plot.title=element_text(size=18,face='bold'),plot.caption=element_text(size=9,hjust=0),legend.position='bottom',plot.margin=margin(15,15,15,15))
world_counts <- world |> left_join(cnt,by='iso3') |> mutate(studies_full=coalesce(studies_full,0L))
world_country <- world |> left_join(country_base,by='iso3')
p <- ggplot(world_country)+geom_sf(aes(fill=if_else(studies>0,per10m,NA_real_)),colour='white',linewidth=.1)+scale_fill_viridis_c(trans='log10',na.value='#e3e0da',name='Studies per 10m people')+map_theme
save(p,'fig_worldmap.webp','Studies examining each country, relative to population',paste('Shading uses the',nrow(countries),'country website list with population data. Grey includes countries with no recorded study or no population in this list.',comma(nrow(geo)),'study-country pairs across',n_distinct(geo$iso3),'named countries in the full geography. Natural Earth medium-resolution polygons; Robinson projection.',base_note),13,8)
centroids <- suppressWarnings(st_centroid(world)) |> group_by(iso3) |> slice_max(as.numeric(st_area(geometry)),n=1,with_ties=FALSE) |> ungroup() |> left_join(cnt,by='iso3') |> left_join(countries |> select(iso3,income),by='iso3') |> filter(studies_full>0)
p <- ggplot(world)+geom_sf(fill='#e9e7e1',colour='white',linewidth=.1)+geom_sf(data=centroids,aes(size=studies_full,colour=income),alpha=.7)+scale_size_area(max_size=17,name='Studies naming country')+scale_colour_manual(values=palette,na.value='#777',name='Income group')+map_theme
save(p,'fig_dotmap.svg','Where economic evaluation studies are conducted',paste('Each bubble represents a country; area is the number of unique included records naming it. Colour uses July 2026 income, grey where unavailable. Locations are study settings, not author affiliations.',comma(nrow(geo)),'study-country pairs across',n_distinct(geo$iso3),'named countries; locations without a matched map polygon have no bubble. Robinson projection.'),13,8)
val <- cnt |> inner_join(burden,by='iso3') |> mutate(per100k=studies_full/dalys*1e5)
w <- world |> left_join(val,by='iso3'); med <- median(val$per100k)
p <- ggplot(w)+geom_sf(aes(fill=per100k),colour='white',linewidth=.1)+scale_fill_viridis_c(trans='log10',na.value='#e3e0da',name='Studies per 100k DALYs')+map_theme
save(p,'fig_map_burden.webp','Research intensity relative to disease burden, by country',paste(nrow(val),'of',nrow(burden),'national GBD 2023 locations have at least one study;',nrow(burden)-nrow(val),'have burden but no study. Median among locations with studies:',round(med,2),'studies per 100,000 DALYs. Grey means no study or no matched national burden row. Robinson projection.',base_note),13,8)
oa_country <- geo |> left_join(m |> select(record_id,oa),by='record_id') |> filter(oa %in% c(0,1)) |> group_by(iso3) |> summarise(n=n(),pct=100*mean(oa),.groups='drop') |> filter(n>=5)
w <- world |> left_join(oa_country,by='iso3')
p <- ggplot(w)+geom_sf(aes(fill=pct),colour='white',linewidth=.1)+scale_fill_gradient(low='#6D91BE',high='#D98F7A',limits=c(0,100),na.value='#e3e0da',name='Open-access share (%)')+map_theme
save(p,'fig_map_openaccess.webp','Where studies are available to read for free',paste('Base:',nrow(oa_country),'countries with at least five unique included records with known open-access status. Grey: fewer than five known-status records or no matching country. Study settings are extracted from titles/abstracts; Robinson projection.',base_note),13,8)
growth <- geo |> left_join(m |> select(record_id,year),by='record_id',suffix=c('_geo','')) |> group_by(iso3) |> summarise(n=n(),pct=100*mean(year>=2018),.groups='drop') |> filter(n>=5)
w <- world |> left_join(growth,by='iso3')
p <- ggplot(w)+geom_sf(aes(fill=pct),colour='white',linewidth=.1)+scale_fill_gradient(low='#D6B264',high='#62A89B',limits=c(0,100),na.value='#e3e0da',name='Share published 2018-2026 (%)')+map_theme
save(p,'fig_map_growth.webp','Where the evidence base contains more recent studies',paste('Base:',nrow(growth),'countries with at least five included records. Colour is the share published in 2018-2026; 2026 is partial. This is the age composition of the evidence, not an estimated annual growth rate. Grey: fewer than five records. Robinson projection.',base_note),13,8)
write_json(manifest,file.path(out,'remaining_figure_manifest.json'),auto_unbox=TRUE,pretty=TRUE)
write_json(list(eligible=nrow(m),study_country_pairs=nrow(geo),topic_coordinates=nrow(pts),openaccess_comparison_n=nrow(oa),country_universe=nrow(countries),national_burden_universe=nrow(burden),rebuilt=length(manifest)),file.path(out,'remaining_figure_counts.json'),auto_unbox=TRUE,pretty=TRUE)
cat(length(manifest),'remaining figures rebuilt from current inputs.\n')
