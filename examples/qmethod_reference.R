# Real, optional R/qmethod reference export. No R output is bundled or invented.
# Run from the repository root after the pinned CI installation:
# Rscript examples/qmethod_reference.R --output-dir /tmp/q-r-reference
# python tests/q/compare_r_reference.py --reference-dir /tmp/q-r-reference
#
# This is synthetic data only. The author's qmethod/psych versions and exact
# normalization/convergence settings are unknown. R 4.4.3, qmethod 1.8.4 and
# psych 2.5.6 are OUR declared reference environment, not the author's setup.
# Official CRAN archives/source hashes and the predeclared comparison tolerances
# are in tests/q/reference-manifest.json. Do not widen tolerance after a failure.
#
# Source inspection: qmethod 1.8.4 R/qmethod.R passes ... to psych::principal;
# psych 2.5.6 R/principal.R passes ... into stats::varimax. The matched run
# explicitly chooses normalize=TRUE and eps=1e-12. A second run keeps eps=1e-5
# and is exported separately as a diagnostic of DEFAULT stopping differences.

args <- commandArgs(trailingOnly = TRUE)
script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_dir <- dirname(normalizePath(sub("^--file=", "", script_arg[[1]])))
option <- function(name, default) {
  indices <- which(args == name)
  if (length(indices) == 0) return(default)
  if (length(indices) != 1 || indices[[1]] == length(args)) stop(paste("Missing or repeated option", name))
  args[[indices[[1]] + 1]]
}
known <- c("--input", "--output-dir", "--scenario")
if (length(args) %% 2 != 0 || (length(args) > 0 && any(!args[seq(1, length(args), 2)] %in% known))) {
  stop("Use --input FILE --output-dir DIRECTORY --scenario baseline|reverse-p03|all")
}
input <- option("--input", file.path(script_dir, "q_synthetic.csv"))
outdir <- option("--output-dir", "q-r-reference")
scenario_option <- option("--scenario", "all")
if (!scenario_option %in% c("baseline", "reverse-p03", "all")) stop("Unknown scenario")
scenarios <- if (scenario_option == "all") c("baseline", "reverse-p03") else scenario_option

expected <- c(R = "4.4.3", qmethod = "1.8.4", psych = "2.5.6")
actual <- c(R = as.character(getRversion()), qmethod = as.character(packageVersion("qmethod")), psych = as.character(packageVersion("psych")))
if (!identical(actual, expected)) stop(paste("Pinned versions required:", paste(names(expected), expected, collapse = ", "), "; found", paste(actual, collapse = ", ")))
suppressPackageStartupMessages(library(qmethod))
options(digits = 17)
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

source <- read.csv(input, check.names = FALSE, fileEncoding = "UTF-8", stringsAsFactors = FALSE)
stopifnot(identical(names(source)[1:2], c("statement_id", "statement")))
stopifnot(!anyDuplicated(names(source)), !anyDuplicated(source$statement_id))
q_baseline <- as.matrix(source[, -(1:2), drop = FALSE]) # D: 20 statements x 10 people
rownames(q_baseline) <- source$statement_id
grid <- c(rep(1, 2), rep(2, 4), rep(3, 8), rep(4, 4), rep(5, 2))
stopifnot(identical(dim(q_baseline), c(20L, 10L)), is.numeric(q_baseline), all(is.finite(q_baseline)))
stopifnot(all(apply(q_baseline, 2, function(x) identical(sort(as.numeric(x)), grid))))
input_sha256 <- digest::digest(file = input, algo = "sha256", serialize = FALSE)
stopifnot(input_sha256 == "4d7edb10053a7695a7cbe5da15d4c12f4fd68d48f0622f38ca3543c829f9c88b")

write_matrix <- function(value, name, directory) {
  # Matrix CSVs preserve row labels and full double precision for comparison.
  write.csv(value, file.path(directory, paste0(name, ".csv")), fileEncoding = "UTF-8", na = "NA")
}

export_run <- function(q, scenario, eps, mode) {
  directory <- file.path(outdir, scenario, mode)
  dir.create(directory, recursive = TRUE, showWarnings = FALSE)
  # Full wrapper: C (10x10) -> PCA/varimax L (10x2) -> flags -> Z/arrays (20x2).
  raw <- qmethod::qmethod(q, nfactors = 2, extraction = "PCA", rotation = "varimax",
                         cor.method = "pearson", forced = TRUE, silent = TRUE,
                         normalize = TRUE, eps = eps)
  raw_loa <- as.matrix(raw$loa)
  stopifnot(identical(dim(raw_loa), c(10L, 2L)), all(is.finite(raw_loa)))
  # Signs and column order have no intrinsic meaning. Canonicalize independently
  # in R, then recompute all postprocessing with the official package functions.
  # Python also verifies the raw->canonical permutation/sign mapping explicitly.
  anchors <- apply(abs(raw_loa), 2, which.max)
  signs <- vapply(seq_len(2), function(j) if (raw_loa[anchors[[j]], j] < 0) -1 else 1, numeric(1))
  factor_order <- order(anchors)
  loa <- sweep(raw_loa, 2, signs, "*")[, factor_order, drop = FALSE]
  colnames(loa) <- c("f1", "f2")
  flagged <- qmethod::qflag(loa = loa, nstat = nrow(q))
  result <- qmethod::qzscores(dataset = q, nfactors = 2, loa = loa, flagged = flagged, forced = TRUE)
  result$qdc <- qmethod::qdc(dataset = q, nfactors = 2, zsc = result$zsc, sed = result$f_char$sd_dif)
  # These two intermediates are calculated from the documented source formula;
  # qmethod does not expose a fictional result$weights or result$weighted_totals.
  floa <- flagged * loa
  weights <- floa / (1 - floa^2)                     # W: 10x2, signed weights
  weighted_totals <- q %*% weights                  # T: 20x2
  ranks <- apply(result$zsc, 2, rank, ties.method = "average")
  correlation <- cor(q, method = "pearson")         # C: 10x10
  pc <- psych::principal(correlation, nfactors = 2, rotate = "none", scores = FALSE)

  write_matrix(q, "data", directory)
  write_matrix(correlation, "correlation", directory)
  write_matrix(matrix(pc$values, ncol = 1), "eigenvalues", directory)
  write_matrix(as.matrix(pc$loadings), "unrotated_loadings", directory)
  write_matrix(raw_loa, "loadings_raw", directory)
  write_matrix(loa, "loadings", directory)
  write_matrix(result$flagged, "flags", directory)
  write_matrix(weights, "weights", directory)
  write_matrix(weighted_totals, "weighted_totals", directory)
  write_matrix(result$zsc, "zscores", directory)
  write_matrix(result$zsc_n, "factor_arrays", directory)
  write_matrix(ranks, "ranks", directory)
  write_matrix(result$f_char$characteristics, "factor_characteristics", directory)
  write_matrix(result$f_char$sd_dif, "sed", directory)
  write_matrix(result$qdc, "distinguishing", directory)
  alignment <- data.frame(canonical_factor = c("F1", "F2"), raw_column = factor_order,
                          sign = signs[factor_order], anchor = colnames(q)[anchors[factor_order]])
  write.csv(alignment, file.path(directory, "alignment.csv"), row.names = FALSE)
  metadata <- c(actual, scenario = scenario, mode = mode,
                nfactors = "2", normalize = "TRUE", eps = format(eps, scientific = TRUE),
                input_sha256 = input_sha256, author_data_reproduced = "FALSE",
                qmethod_source_sha256 = "c672fbf62c684e4cc6c8be4e4a07ab89cb72939b5397e128e9b1b38b30c6b36a",
                psych_source_sha256 = "ced7eb0ef4e6be7ddab22b0b3f934d3dbd25eefc394067ff9fa1a916ec315110")
  write.csv(data.frame(key = names(metadata), value = unname(metadata)), file.path(directory, "metadata.csv"), row.names = FALSE)
  saveRDS(raw, file.path(directory, "raw_qmethod_result.rds"))
  saveRDS(result, file.path(directory, "canonical_qmethod_result.rds"))
}

for (scenario in scenarios) {
  q <- q_baseline
  if (scenario == "reverse-p03") {
    stopifnot("P03" %in% colnames(q))
    q[, "P03"] <- 6 - q[, "P03"]
  }
  export_run(q, scenario, eps = 1e-12, mode = "matched")
  export_run(q, scenario, eps = 1e-5, mode = "native-default")
}
capture.output(sessionInfo(), file = file.path(outdir, "R_session_info.txt"))
write.csv(installed.packages()[, c("Package", "Version"), drop = FALSE],
          file.path(outdir, "R_package_versions.csv"), row.names = FALSE)
message("Real R outputs exported; run the Python comparator before claiming numerical agreement.")
