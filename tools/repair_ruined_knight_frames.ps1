# Compatibility entry point. The authored walking source is now split by the
# dedicated installer instead of duplicating one pose over the whole cycle.
& (Join-Path $PSScriptRoot 'install_ruined_knight_walk.ps1') @args
