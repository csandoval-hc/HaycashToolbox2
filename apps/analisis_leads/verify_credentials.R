args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) quit(status = 2)

user <- args[[1]]
pwd  <- args[[2]]

suppressPackageStartupMessages({
  library(shinymanager)
})

passphrase <- Sys.getenv("SM_PASSPHRASE", unset = "frase-secreta-larga-y-unica")

ok <- FALSE
try({
  checker <- check_credentials(db = "data/auth.sqlite", passphrase = passphrase)
  res <- checker(user, pwd)
  ok <- isTRUE(res$result)
}, silent = TRUE)

if (isTRUE(ok)) {
  quit(status = 0)
} else {
  quit(status = 1)
}
