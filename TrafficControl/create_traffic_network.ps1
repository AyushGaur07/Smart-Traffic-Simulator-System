$ErrorActionPreference = "Stop"
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
$netconvert = Join-Path $env:SUMO_HOME "bin\netconvert.exe"
$randomTrips = Join-Path $env:SUMO_HOME "tools\randomTrips.py"

if (!(Test-Path $netconvert)) { throw "Cannot find netconvert.exe at $netconvert" }
if (!(Test-Path $randomTrips)) { throw "Cannot find randomTrips.py at $randomTrips" }

$nodesFile = Join-Path $PSScriptRoot "nodes.nod.xml"
$edgesFile = Join-Path $PSScriptRoot "edges.edg.xml"
$networkFile = Join-Path $PSScriptRoot "network.net.xml"
$routesFile = Join-Path $PSScriptRoot "routes.rou.xml"

@'
<nodes>
  <node id="N" x="0" y="200" type="priority"/>
  <node id="S" x="0" y="-200" type="priority"/>
  <node id="E" x="200" y="0" type="priority"/>
  <node id="W" x="-200" y="0" type="priority"/>
  <node id="C" x="0" y="0" type="traffic_light"/>
</nodes>
'@ | Set-Content -Encoding utf8 $nodesFile

@'
<edges>
  <edge id="N_C" from="N" to="C" numLanes="1" speed="13.89"/>
  <edge id="C_N" from="C" to="N" numLanes="1" speed="13.89"/>
  <edge id="S_C" from="S" to="C" numLanes="1" speed="13.89"/>
  <edge id="C_S" from="C" to="S" numLanes="1" speed="13.89"/>
  <edge id="E_C" from="E" to="C" numLanes="1" speed="13.89"/>
  <edge id="C_E" from="C" to="E" numLanes="1" speed="13.89"/>
  <edge id="W_C" from="W" to="C" numLanes="1" speed="13.89"/>
  <edge id="C_W" from="C" to="W" numLanes="1" speed="13.89"/>
</edges>
'@ | Set-Content -Encoding utf8 $edgesFile

Write-Host "Generating left-hand-traffic network..."
& $netconvert --node-files $nodesFile --edge-files $edgesFile --lefthand true --output-file $networkFile
if ($LASTEXITCODE -ne 0) { throw "netconvert failed." }

Write-Host "Generating trips at a moderate rate..."
python $randomTrips -n $networkFile -r $routesFile -e 600 --period 3 --seed 42 --validate
if ($LASTEXITCODE -ne 0) { throw "randomTrips failed." }

Write-Host "Created network.net.xml and routes.rou.xml."
