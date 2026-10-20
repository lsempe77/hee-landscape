# theme_hee (ggplot) version of 09_evidence_types_and_growth: publication type, evaluation type and growth.
# Reads the aggregated source tables written by create_manuscript_evidence_types_oct19.py; never writes docs/.
# Run: Rscript scripts/create_manuscript_evidence_types_oct19.R [repo root]
suppressPackageStartupMessages({library(dplyr);library(tidyr);library(readr);library(ggplot2);library(patchwork)})
args <- commandArgs(trailingOnly=TRUE)
root <- normalizePath(if(length(args)) args[[1]] else '.',winslash='/')
source(file.path(root,'docs/theme_hee.R'))
out <- file.path(root,'manuscript figures Oct 19'); src <- file.path(out,'source data')
counts <- read_csv(file.path(src,'evidence_types_counts.csv'),show_col_types=FALSE)
by_year <- read_csv(file.path(src,'evidence_types_by_year.csv'),show_col_types=FALSE)
pub <- counts |> filter(group=='Publication type')
evt <- counts |> filter(group!='Publication type')
stopifnot(pub$n==c(38958,667,1985),evt$n==c(19097,10150,9020,1358),sum(by_year$all)==41610)

n <- sum(pub$n); n_full <- sum(evt$n); last <- max(by_year$year)
since <- sum(by_year$all[by_year$year>=2020])
review_col <- '#c9c8c3'
types <- c('Cost-utility'='Cost-utility (CUA)','Cost-effectiveness'='Cost-effectiveness (CEA)',
           'Cost-consequence'='Cost-consequence (CCA)','Cost-benefit'='Cost-benefit (CBA)',
           'Review (no evaluation type)'='Review only')
fills <- c(pal_eval[names(types)[1:4]],'Review (no evaluation type)'=review_col)
pct <- function(x,d=1) paste0(formatC(100*x,format='f',digits=d),'%')
panel_title <- theme(plot.title=element_text(face='bold',size=10.5,colour=hee_ink$primary,margin=margin(b=6)))

# A: one bar of all publications
a <- pub |> mutate(xmax=cumsum(n),xmin=xmax-n,fill=c(hee_ink$secondary,hee_ink$muted,review_col))
sa <- a$n[1]; wr <- a$n[2]; ro <- a$n[3]
pA <- ggplot(a)+
  geom_rect(aes(xmin=xmin,xmax=xmax,ymin=0,ymax=1,fill=fill),colour=hee_ink$surface,linewidth=.4)+
  scale_fill_identity()+
  annotate('text',x=sa/2,y=.5,label=sprintf('Stand-alone full economic evaluation  %s (%s)',format(sa,big.mark=','),pct(sa/n)),
           colour=hee_ink$surface,fontface='bold',size=3.2)+
  annotate('segment',x=sa+wr/2,xend=sa-4800,y=1,yend=1.55,colour=hee_ink$muted,linewidth=.25)+
  annotate('text',x=sa-4900,y=1.6,label=sprintf('Evaluation that also includes a review  %s (%s)',wr,pct(wr/n)),
           hjust=1,vjust=0,size=2.9,colour=hee_ink$secondary)+
  annotate('segment',x=sa+wr+ro/2,xend=n-300,y=1,yend=1.55,colour=hee_ink$muted,linewidth=.25)+
  annotate('text',x=n,y=1.6,label=sprintf('Review only  %s (%s)',format(ro,big.mark=','),pct(ro/n)),
           hjust=1,vjust=0,size=2.9,colour=hee_ink$secondary)+
  annotate('segment',x=c(0,0,sa+wr),xend=c(0,sa+wr,sa+wr),y=c(-.25,-.4,-.4),yend=c(-.4,-.4,-.25),colour=hee_ink$secondary,linewidth=.3)+
  annotate('text',x=0,y=-.55,label=sprintf('Original full economic evaluations  %s (%s)',format(n_full,big.mark=','),pct(n_full/n)),
           hjust=0,vjust=1,size=3,fontface='bold',colour=hee_ink$primary)+
  scale_x_continuous(limits=c(0,n),expand=c(0,0))+scale_y_continuous(limits=c(-1.1,2.1),expand=c(0,0))+
  labs(title=sprintf('A  Publication type (n = %s)',format(n,big.mark=',')))+
  theme_hee(grid='none')+panel_title+theme(axis.text=element_blank(),axis.title=element_blank())

# B: shares among original evaluations
b <- evt |> mutate(y=rev(seq_len(n())),label=types[category],m=max(n))
pB <- ggplot(b,aes(y=y))+
  geom_rect(aes(xmin=0,xmax=n,ymin=y-.2,ymax=y+.2,fill=category))+
  geom_text(aes(x=0,y=y+.28,label=label),hjust=0,vjust=0,size=2.9,colour=hee_ink$secondary)+
  geom_text(aes(x=n+m*.025,label=pct(share)),hjust=0,size=3.4,fontface='bold',colour=hee_ink$primary)+
  geom_text(aes(x=n+m*.17,label=paste0('(',format(n,big.mark=',',trim=TRUE),')')),hjust=0,size=2.6,colour=hee_ink$secondary)+
  scale_fill_manual(values=fills,guide='none')+
  scale_x_continuous(limits=c(0,max(b$n)*1.4),expand=c(0,0))+scale_y_continuous(limits=c(.6,4.75),expand=c(0,0))+
  labs(title=sprintf('B  Evaluation type, original evaluations (n = %s)',format(n_full,big.mark=',')))+
  theme_hee(grid='none')+panel_title+theme(axis.text=element_blank(),axis.title=element_blank())

# C: publications per year by type; the incomplete final year is drawn faded
c_long <- by_year |> select(-all) |> pivot_longer(-year,names_to='type',values_to='n') |>
  mutate(type=factor(type,levels=names(types)),partial=year==last)
top <- max(by_year$all)
pC <- ggplot(c_long,aes(year,n,fill=type,alpha=partial))+
  annotate('rect',xmin=2019.5,xmax=last+.5,ymin=0,ymax=top*1.2,fill=hee_ink$grid,alpha=.6)+
  geom_col(width=.74,position=position_stack(reverse=TRUE))+
  annotate('text',x=2020+(last-2020)/2,y=top*1.11,lineheight=1.1,size=3,fontface='bold',colour=hee_ink$primary,
           label=sprintf('%s of all publications (%s)\nappeared 2020–%d',pct(since/n,0),format(since,big.mark=','),last))+
  scale_fill_manual(values=fills,labels=types)+
  scale_alpha_manual(values=c(`FALSE`=1,`TRUE`=.45),guide='none')+
  scale_x_continuous(breaks=c(seq(2010,2024,2),last),labels=c(seq(2010,2024,2),paste0(last,'*')),expand=c(.01,0))+
  scale_y_continuous(labels=scales::comma,limits=c(0,top*1.2),expand=c(0,0))+
  labs(title=sprintf('C  Publications per year (n = %s)',format(n,big.mark=',')),x=NULL,y='Publications')+
  theme_hee(grid='y')+panel_title+guides(fill=guide_legend(nrow=2,byrow=TRUE))

caption <- sprintf(paste0('Eligible publications, 2010–%d. Original full economic evaluations compare both costs and consequences; %s of them also report a review ',
  "(for example, a systematic review followed by the authors' own evaluation). Reviews only synthesise published evaluations and report no evaluation of their own. ",
  'Panel B: each original evaluation has one primary type. Panel C: shading marks 2020 onwards; *%d is incomplete (searches ran to August %d), so its bar is faded.'),
  last,wr,last,last)
fig <- pA/(pB|pC)+plot_layout(heights=c(1,3.3),widths=c(1,1.75))+
  plot_annotation(title=sprintf('Types of health economic evidence and their growth, 2010–%d',last),caption=caption,theme=theme_hee())
stem <- file.path(out,'09_evidence_types_and_growth_R')
ggsave(paste0(stem,'.png'),fig,width=11,height=7.6,dpi=300,device=ragg::agg_png,bg=hee_ink$surface)
ggsave(paste0(stem,'.pdf'),fig,width=11,height=7.6,device=cairo_pdf,bg=hee_ink$surface)
ggsave(paste0(stem,'.svg'),fig,width=11,height=7.6,device=svglite::svglite,bg=hee_ink$surface)
cat('Saved 09_evidence_types_and_growth_R\n')
