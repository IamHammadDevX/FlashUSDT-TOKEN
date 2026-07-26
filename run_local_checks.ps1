$ErrorActionPreference = "Stop"

Write-Host "== Python dependencies =="
python -m pip install -r flashDemotoken_generator\requirements.txt

Write-Host "== Solidity compile =="
Push-Location flashDemotoken_generator
npx.cmd hardhat compile

Write-Host "== Solidity tests =="
npx.cmd hardhat test
Pop-Location

Write-Host "== Python tests =="
$env:PYTHONPATH = Join-Path (Get-Location) "flashDemotoken_generator"
python -m pytest

Write-Host "== Python syntax check =="
python -m compileall flashDemotoken_generator tests

Write-Host "All local checks passed."
