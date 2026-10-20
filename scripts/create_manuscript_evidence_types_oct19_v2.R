# theme_hee (ggplot) v2 of the evidence-types figure, in the KPI/track-bar style of the concentration figure:
# blue bars on grey tracks, bold labels above, large headline numbers, green for 2020 onwards.
# Reads the aggregated source tables written by create_manuscript_evidence_types_oct19.py; never writes docs/.
# Run: Rscript scripts/create_manuscript_evidence_types_oct19_v2.R [repo root]
suppressPackageStartupMessages({library(dplyr);library(readr);library(ggplot2);library(patchwork)})
args <- commandArgs(trailingOnly=TRUE)
root <- normalizePath(if(length(args)) args[[1]] else '.',winslash='/')
source(file.path(root,'docs/theme_hee.R'))
out <- file.path(root,'manuscript figures Oct 19'); src <- file.path(out,'source data')
counts <- read_csv(file.path(src,'evidence_types_counts.csv'),show_col_types=FALSE)
by_year <- read_csv(file.path(src,'evidence_types_by_year.csv'),show_col_types=FALSE)
pub <- counts |> filter(group=='Publication type'); evt <- counts |> filter(group!='Publication type')
stopifnot(pub$n==c(38958,667,1985),evt$n==c(19097,10150,9020,1358),sum(by_year$all)==41610)

blue <- hee_cat[['blue']]; green <- hee_cat[['green']]; track <- '#e8e7e3'
n <- sum(pub$n); n_full <- sum(evt$n); sa <- pub$n[1]; wr <- pub$n[2]; ro <- pub$n[3]
last <- max(by_year$year); since <- sum(by_year$all[by_year$year>=2020])
growth <- by_year$all[by_year$year==last-1]/by_year$all[by_year$year==2010]
comma <- function(x) format(x,big.mark=',',trim=TRUE)
pct <- function(x,d=1) paste0(formatC(100*x,format='f',digits=d),'%')
panel <- theme_hee(grid='none')+theme(plot.title=element_text(face='bold',size=11,colour=hee_ink$primary,margin=margin(b=8)),
                                      axis.title.y=element_blank(),axis.text.y=element_blank())

# Bold label above a blue bar on a full-width grey track; value at the bar end; note underneath.
tracks <- function(d,title,xlab){
  d <- d |> mutate(y=4-seq_len(n())+1,inside=share>.85)
  ggplot(d)+
    geom_rect(aes(xmin=0,xmax=1,ymin=y-.13,ymax=y+.13),fill=track)+
    geom_rect(aes(xmin=0,xmax=share,ymin=y-.13,ymax=y+.13),fill=blue)+
    geom_text(aes(x=0,y=y+.2,label=label),hjust=0,vjust=0,size=3,fontface='bold',colour=hee_ink$primary)+
    geom_text(aes(x=if_else(inside,share-.012,share+.012),y=y,label=pct(share),hjust=if_else(inside,1,0),colour=inside),size=2.8,fontface='bold')+
    scale_colour_manual(values=c(`TRUE`=hee_ink$surface,`FALSE`=hee_ink$primary),guide='none')+
    geom_text(aes(x=0,y=y-.2,label=note),hjust=0,vjust=1,size=2.5,colour=hee_ink$secondary)+
    scale_x_continuous(limits=c(0,1),breaks=seq(0,1,.25),labels=scales::label_percent(),expand=expansion(mult=c(0,.02)))+
    scale_y_continuous(limits=c(.45,4.62),expand=c(0,0))+
    labs(title=title,x=xlab)+panel
}

pA <- tracks(tibble(label=c('Original full economic evaluations','   of which stand-alone','   of which also conducted a review','Reviews only'),
                    share=c(sa+wr,sa,wr,ro)/n,
                    note=c(sprintf('n = %s',comma(sa+wr)),sprintf('   n = %s',comma(sa)),
                           sprintf("   n = %s; e.g. a systematic review followed by the authors' own evaluation",comma(wr)),
                           sprintf('Synthesise published evaluations; no evaluation of their own (n = %s)',comma(ro)))),
             sprintf('A  Publication type (n = %s)',comma(n)),'Share of all publications')
pB <- tracks(evt |> mutate(label=c('Cost-utility analysis (CUA)','Cost-effectiveness analysis (CEA)','Cost-consequence analysis (CCA)','Cost-benefit analysis (CBA)'),
                           note=paste0('n = ',comma(n))),
             sprintf('B  Evaluation type (original evaluations, n = %s)',comma(n_full)),'Share of original evaluations')

yrs <- by_year |> mutate(period=if_else(year>=2020,'2020 onwards','2010–2019'),partial=year==last)
pC <- ggplot(yrs,aes(year,all,fill=period,alpha=partial))+
  geom_col(width=.72)+
  annotate('text',x=2023,y=max(yrs$all)*1.13,label=sprintf('%s since 2020',pct(since/n,0)),size=3,fontface='bold',colour=green)+
  scale_fill_manual(values=c('2010–2019'=blue,'2020 onwards'=green),guide='none')+
  scale_alpha_manual(values=c(`FALSE`=1,`TRUE`=.45),guide='none')+
  scale_x_continuous(breaks=c(seq(2010,2024,2),last),labels=c(seq(2010,2024,2),paste0(last,'*')),expand=c(.01,0))+
  scale_y_continuous(labels=scales::comma,limits=c(0,max(yrs$all)*1.2),expand=c(0,0))+
  labs(title=sprintf('C  Publications per year, 2010–%d',last),x=NULL,y='Publications')+
  theme_hee(grid='y')+theme(plot.title=element_text(face='bold',size=11,colour=hee_ink$primary,margin=margin(b=8)))

kpi <- function(y,value,text,col) list(annotate('text',x=0,y=y,label=value,hjust=0,vjust=0,size=8,fontface='bold',colour=col),
                                       annotate('text',x=0,y=y-.06,label=text,hjust=0,vjust=1,size=2.6,colour=hee_ink$secondary,lineheight=1.1))
pD <- ggplot()+
  kpi(.78,pct(since/n,0),sprintf('of all publications (%s of %s)\nappeared in 2020–%d',comma(since),comma(n),last),green)+
  kpi(.4,sprintf('%.1f times',growth),sprintf('as many publications in %d as in 2010\n(%s vs %s)',last-1,comma(by_year$all[by_year$year==last-1]),comma(by_year$all[by_year$year==2010])),blue)+
  scale_x_continuous(limits=c(0,1),expand=c(0,0))+scale_y_continuous(limits=c(0,1),expand=c(0,0))+
  labs(title='D  Growth of the evidence')+theme_void()+
  theme(plot.title=element_text(face='bold',size=11,colour=hee_ink$primary,margin=margin(b=8)),plot.background=element_rect(fill=hee_ink$surface,colour=NA))

caption <- sprintf(paste0('Eligible publications, 2010–%d. Original full economic evaluations compare both costs and consequences; %s also report a review ',
  "(for example, a systematic review followed by the authors' own evaluation). Each original evaluation has one primary type. ",
  'C: green marks 2020 onwards; *%d is incomplete (searches ran to August %d), so its bar is faded and D compares %d with 2010.'),
  last,comma(wr),last,last,last-1)
fig <- wrap_elements(full=pA|pB)/(pC|pD)+plot_layout(heights=c(1,1.15),widths=c(1.35,1))+
  plot_annotation(title=sprintf('Types of health economic evidence and their growth, 2010–%d',last),caption=caption,theme=theme_hee())
stem <- file.path(out,'09_evidence_types_and_growth_R_v2')
ggsave(paste0(stem,'.png'),fig,width=11,height=7.4,dpi=300,device=ragg::agg_png,bg=hee_ink$surface)
ggsave(paste0(stem,'.pdf'),fig,width=11,height=7.4,device=cairo_pdf,bg=hee_ink$surface)
ggsave(paste0(stem,'.svg'),fig,width=11,height=7.4,device=svglite::svglite,bg=hee_ink$surface)
cat('Saved 09_evidence_types_and_growth_R_v2\n')
