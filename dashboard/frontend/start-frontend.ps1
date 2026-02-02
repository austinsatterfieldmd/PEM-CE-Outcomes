$nodePath = "c:\Users\snair\OneDrive - MJH\Documents\GitHub\Steve-V2-Outcomes-Tagger\CME-Outcomes-Tagger_v2\node-v20.10.0-win-x64"
$env:Path = $nodePath + ";" + $env:Path
Set-Location "c:\Users\snair\OneDrive - MJH\Documents\GitHub\Steve-V2-Outcomes-Tagger\CME-Outcomes-Tagger_v2\dashboard\frontend"
npm run dev
