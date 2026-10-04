# Optional R/vegan reference for the SAME SYNTHETIC data; not executed here.
# Not Cheng2023's original35-village matrix or Fig7 plot settings.
library(vegan)
d <- read.csv('rda_synthetic_villages.csv', check.names=FALSE)
stopifnot(!anyDuplicated(d$village_id), nrow(d)==4)
Y <- scale(as.matrix(d[c('perception_a','perception_b')]))
X <- scale(as.matrix(d[c('crop_share_percent','distance_km')]))
rownames(Y) <- rownames(X) <- d$village_id
# Response matrix first, explanatory matrix second. Already scaled explicitly.
fit <- rda(Y, X, scale=FALSE)
lambda <- eigenvals(fit, model='constrained')
total <- sum(apply(Y, 2, var))
print(cbind(lambda=lambda, fraction_of_total=lambda/total,
            fraction_of_constrained=lambda/sum(lambda)))
# Independently expose the same centered regression mechanism, not plot scores.
Yhat <- X %*% qr.solve(X,Y)
E <- Y-Yhat
print(Yhat); print(E); print(t(X)%*%E)
v <- eigen(cov(Yhat), symmetric=TRUE)
axes <- Yhat %*% v$vectors
print(cor(cbind(X,Y),axes))
# Axis sign/order is arbitrary; align before comparing with the teaching display.
# Do not claim these correlation coordinates equal vegan scaling1/2 or originalFig7.
# No permutation p-value is presented for these4 invented rows.
print(sessionInfo())
