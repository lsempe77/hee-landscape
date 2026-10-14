# Rebuild only fig_intervention_map (reconciled) with a readable legend.
# Same data steps as scripts/build_remaining_figures_reconciled.R (kept, not re-run here,
# because its install step also rewrites docs/v2 and docs/v3). Changes: legend dots
# enlarged and fully opaque, legend in two rows. Frozen topic coordinates, filtered.
# Usage: Rscript scripts/build_intervention_map_legend.R <repo root> <output .png>; then convert to
# docs/figures/fig_intervention_map_reconciled.webp (the file the site shows).
suppressPackageStartupMessages({library(dplyr);library(readr);library(ggplot2);library(scales);library(patchwork)})
args <- commandArgs(trailingOnly=TRUE)
root <- normalizePath(if(length(args)) args[[1]] else '.',winslash='/')
raw <- file.path(root,'data/raw')
rd <- function(file) read_csv(file.path(raw,file),col_types=cols(.default='c'),show_col_types=FALSE,na=c('','NA'))
m <- rd('hee_analysis_master_v2_1.csv') |> filter(is_eligible=='TRUE')
stopifnot(nrow(m)==41610L,!anyDuplicated(m$record_id))
m <- m |> left_join(rd('hee_intervention_class.csv') |> select(record_id,intervention_class),by='record_id')
groups <- c('Low income','Lower middle income','Upper middle income','High income')
single <- m |> filter(geo_scope=='single_country',income_group_pubyear %in% groups) |>
  mutate(side=if_else(income_group_pubyear=='High income','High-income settings','Low- and middle-income settings'))
class_lab <- c(pharma='Pharmaceuticals',vaccine='Vaccines',screening_diagnostic='Screening & diagnosis',surgical_procedural='Surgery & procedures',device_or_supply='Devices & supplies',behavioural_preventive='Behavioural & preventive',care_model_organisational='Care models & organisation',financing_payment_policy='Financing & payment policy',other='Other')
bg <- '#FAF9F7'; ink <- '#10243e'
theme_set(theme_minimal(base_family='Arial',base_size=11)+theme(plot.background=element_rect(fill=bg,colour=NA),panel.background=element_rect(fill=bg,colour=NA),plot.title=element_text(face='bold',size=18,colour=ink),plot.caption=element_text(size=9,hjust=0,lineheight=1.2),plot.margin=margin(16,18,16,18),legend.position='bottom'))
wrap <- function(s,width=125) paste(strwrap(s,width=width),collapse='\n')
income_note <- 'Study-level income groups use the World Bank classification in force on 1 January of publication year. Country-level colours use July 2026 groups.'

pts <- rd('topic_map.csv') |> filter(record_id %in% m$record_id) |> mutate(x=as.numeric(x),y=as.numeric(y),cluster=as.integer(cluster)) |> left_join(m |> select(record_id,intervention_class),by='record_id')
stopifnot(nrow(pts)==41583L)
class_rates <- single |> filter(!is.na(intervention_class)) |> group_by(intervention_class) |> summarise(n=n(),lmic=100*mean(side=='Low- and middle-income settings'),.groups='drop')
pts <- pts |> left_join(class_rates,by='intervention_class') |> mutate(class=if_else(cluster==-1,NA_character_,unname(class_lab[intervention_class])))
classes <- setNames(c('#6D91BE','#D98F7A','#9B87B8','#b23a48','#D6B264','#62A89B','#16a085','#a0522d','#888'),unname(class_lab))
legend_labels <- setNames(paste0(unname(class_lab[class_rates$intervention_class]),' (',round(class_rates$lmic),'% LMIC)'),unname(class_lab[class_rates$intervention_class]))
big_keys <- guide_legend(nrow=3,override.aes=list(size=5,alpha=1),title.position='top')
pa <- ggplot(pts,aes(x,y))+geom_point(aes(colour=class),size=.35,alpha=.65)+
  scale_colour_manual(values=classes,na.value='#ddd',na.translate=FALSE,name='Primary intervention',labels=function(x) unname(legend_labels[x]))+
  guides(colour=big_keys)+coord_equal()+theme_void()+
  theme(legend.position='bottom',legend.text=element_text(size=11),legend.title=element_text(size=12,face='bold'),legend.key.size=unit(16,'pt'))+
  labs(title='A | Primary intervention')
pb <- ggplot(pts,aes(x,y))+geom_point(aes(colour=if_else(cluster==-1,NA_real_,lmic)),size=.35,alpha=.65)+
  scale_colour_gradient(low='#6D91BE',high='#D98F7A',limits=c(0,100),na.value='#ddd',name='LMIC share (%)')+
  guides(colour=guide_colourbar(direction='horizontal',barwidth=unit(12,'lines'),barheight=unit(.8,'lines'),title.position='top'))+
  coord_equal()+theme_void()+theme(legend.text=element_text(size=10),legend.title=element_text(size=12,face='bold'))+
  labs(title='B | Share of each intervention class in LMIC settings')
caption <- paste('Base:',comma(nrow(pts)),'eligible records with frozen topic coordinates; 27 included records have no coordinates. Grey points are HDBSCAN noise or missing intervention labels. LMIC shares are computed among',comma(nrow(single)),'single-country records with known publication-year income, by primary intervention class. Coordinates were filtered, not refitted.',income_note)
p <- (pa+pb+plot_layout(guides='collect'))+plot_annotation(title='What kinds of healthcare does the research cover?',caption=wrap(caption),
  theme=theme(plot.title=element_text(face='bold',size=18),plot.caption=element_text(size=9,hjust=0)))&
  theme(legend.position='bottom',legend.box='horizontal',legend.box.just='left',legend.justification='center')
out_png <- if(length(args)>1) args[[2]] else file.path(root,'exports/fig_intervention_map_reconciled.png')
ggsave(out_png,p,width=15,height=9.6,dpi=170,bg=bg,device=ragg::agg_png,limitsize=FALSE)
cat('fig_intervention_map_reconciled.png rebuilt;',nrow(single),'single-country records\n')
