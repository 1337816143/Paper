# Synthetic teaching example; NOT authors' code or Quzhou/Hainan observations.
# R base functions only. Run with Rscript multivariate_lab.R.
set.seed(19)
X <- data.frame(profit=rnorm(30,100,10), water=rnorm(30,50,6), labour=rnorm(30,80,8))
stopifnot(!anyNA(X), all(vapply(X, sd, numeric(1)) > 0))
pc <- prcomp(X, center=TRUE, scale.=TRUE)
print(summary(pc))
# Retaining two PCs is an educational choice, not a paper-specific setting.
hc <- hclust(dist(pc$x[,1:2,drop=FALSE]), method='ward.D2')
group <- cutree(hc,k=3)
print(aggregate(X,list(cluster=group),mean))
write.csv(data.frame(X,cluster=group),'synthetic_cluster_output.csv',row.names=FALSE)
# For scientific use, assess variable selection, PCs, cluster stability and context.
