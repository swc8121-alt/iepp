param(
  [switch]$CheckOnly,
  [string]$VMNameA,
  [string]$VMNameB,
  [string]$GuestUser,
  [ValidateSet('auto', 'linux', 'windows')]
  [string]$GuestOS = 'auto'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorLog = Join-Path $Root 'IEPP_A3_LAST_ERROR.txt'

trap {
  $Message = ($_ | Out-String).Trim()
  $Recorded = @(
    'IEPP A3 v0.2.4.2 failure record'
    ('Time: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss K'))
    ''
    $Message
  ) -join [Environment]::NewLine
  try { [IO.File]::WriteAllText($ErrorLog, $Recorded, [Text.UTF8Encoding]::new($false)) } catch {}
  Write-Host "`n[IEPP] The run stopped safely." -ForegroundColor Red
  Write-Host $Message -ForegroundColor Red
  Write-Host "Error saved to: $ErrorLog" -ForegroundColor Yellow
  exit 1
}

function Write-Step([string]$Text) { Write-Host "`n[IEPP] $Text" -ForegroundColor Cyan }
function Find-Program([string]$Name, [string[]]$Candidates) {
  $command = Get-Command $Name -ErrorAction SilentlyContinue
  if ($command) { return $command.Source }
  foreach ($candidate in $Candidates) { if (Test-Path -LiteralPath $candidate) { return $candidate } }
  return $null
}

Write-Host 'IEPP A3 Two-VM Controlled-Race Batch' -ForegroundColor White
Write-Host 'Runner v0.2.4.2 - 22 trials - L1 claim boundary' -ForegroundColor DarkGray

$Node = Find-Program 'node.exe' @('C:\Program Files\nodejs\node.exe')
$VBox = Find-Program 'VBoxManage.exe' @('C:\Program Files\Oracle\VirtualBox\VBoxManage.exe')

Write-Step 'Host preflight'
$NodeOK = $false
if ($Node) {
  $NodeVersion = (& $Node --version).Trim()
  $NodeMajor = [int](($NodeVersion.TrimStart('v') -split '\.')[0])
  if ($NodeMajor -ge 22) { $NodeOK = $true; Write-Host "  [PASS] Node: $NodeVersion" -ForegroundColor Green }
  else { Write-Host "  [FAIL] Node.js 22 or newer is required; found $NodeVersion." -ForegroundColor Red }
} else { Write-Host '  [FAIL] Node.js 22 or newer is required on the host.' -ForegroundColor Red }
if ($VBox) { Write-Host "  [PASS] VirtualBox: $(& $VBox --version)" -ForegroundColor Green } else { Write-Host '  [FAIL] Oracle VM VirtualBox is required.' -ForegroundColor Red }
if (-not $NodeOK -or -not $VBox) {
  Write-Host "`nInstall the missing dependency, then run this file again." -ForegroundColor Yellow
  Read-Host 'Press Enter to close'
  exit 2
}

Write-Step 'Registered VirtualBox VMs'
$VmList = & $VBox list vms
if ($LASTEXITCODE -ne 0) { throw 'Unable to read the VirtualBox VM list.' }
if ($VmList) { $VmList | ForEach-Object { Write-Host "  $_" } } else { Write-Host '  No registered VMs were found.' -ForegroundColor Yellow }

if ($CheckOnly) {
  Write-Host "`nPreflight completed." -ForegroundColor Green
  Write-Host 'The live A3 run requires TWO DISTINCT disposable VMs.' -ForegroundColor Yellow
  Write-Host 'Install Guest Additions and Node.js 22+ in both guests before starting.' -ForegroundColor Green
  Read-Host 'Press Enter to close'
  exit 0
}

if (-not $VMNameA) { $VMNameA = Read-Host 'Enter the exact VM A name' }
if (-not $VMNameB) { $VMNameB = Read-Host 'Enter the exact VM B name' }
if (-not $GuestUser) { $GuestUser = Read-Host 'Enter the test-account name used inside both guests' }
if ([string]::IsNullOrWhiteSpace($VMNameA) -or [string]::IsNullOrWhiteSpace($VMNameB) -or [string]::IsNullOrWhiteSpace($GuestUser)) { throw 'Both VM names and the guest account are required.' }
if ($VMNameA -ceq $VMNameB) { throw 'VM A and VM B must be different registered VMs.' }

foreach ($Name in @($VMNameA, $VMNameB)) {
  & $VBox showvminfo $Name --machinereadable *> $null
  if ($LASTEXITCODE -ne 0) { throw "VM '$Name' was not found." }
}

Write-Host "`nWARNING: This test powers off BOTH VMs and restores v0.2.4.2 snapshots." -ForegroundColor Yellow
Write-Host 'Never run it on an important work VM.' -ForegroundColor Yellow
$confirm = Read-Host "Type RUN A3 only if '$VMNameA' and '$VMNameB' are disposable test VMs"
if ($confirm -cne 'RUN A3') { Write-Host 'Run cancelled by the user.'; exit 1 }

$SecurePassword = Read-Host 'Enter the shared VM test-account password (input is hidden)' -AsSecureString
$Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
$PasswordFile = Join-Path ([IO.Path]::GetTempPath()) ('iepp-a3-' + [guid]::NewGuid().ToString('N') + '.txt')
$Output = Join-Path $Root ('evidence-vm-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$TranscriptStarted = $false

try {
  New-Item -ItemType Directory -Path $Output -Force *> $null
  try {
    Start-Transcript -LiteralPath (Join-Path $Output 'console-transcript.txt') -Force *> $null
    $TranscriptStarted = $true
  } catch {}
  $PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
  [IO.File]::WriteAllText($PasswordFile, $PlainPassword, [Text.UTF8Encoding]::new($false))
  $Identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
  & icacls.exe $PasswordFile /inheritance:r /grant:r "${Identity}:(F)" *> $null
  $PlainPassword = $null

  Write-Step 'Starting the 22-trial two-VM batch'
  $RunnerArgs = @(
    (Join-Path $Root 'run.mjs'),
    '--vm-a', $VMNameA,
    '--vm-b', $VMNameB,
    '--guest-user', $GuestUser,
    '--password-file', $PasswordFile,
    '--guest-os', $GuestOS,
    '--vboxmanage', $VBox,
    '--output', $Output
  )
  & $Node @RunnerArgs
  if ($LASTEXITCODE -ne 0) { throw 'The A3 batch stopped on a fail-closed condition. Preserve the evidence folder and the screen error.' }

  Write-Step 'Verifying hashes, evidence chain, registry events, and race invariants'
  & $Node (Join-Path $Root 'verify-bundle.mjs') $Output
  if ($LASTEXITCODE -ne 0) { throw 'Evidence-bundle integrity verification failed.' }

  $Summary = Get-Content -LiteralPath (Join-Path $Output 'summary.json') -Raw | ConvertFrom-Json
  if (-not $Summary.execution.actual_vm_executed) { throw 'actual_vm_executed is false. This bundle is not live VM evidence.' }
  if ($Summary.execution.distinct_vm_count -ne 2) { throw 'The bundle does not record two distinct VMs.' }
  if ($Summary.passed_trials -ne 22 -or $Summary.total_trials -ne 22) { throw 'The full 22-trial matrix did not pass.' }
  if ($Summary.race_metrics.race_trials -ne 8 -or $Summary.race_metrics.server_processing_overlap_trials -ne 8) { throw 'Not every controlled race has server-observed request overlap.' }
  if ($Summary.race_metrics.cas_overlap_trials -ne 0 -or $Summary.race_metrics.single_accept_trials -ne 8) { throw 'The atomic single-successor invariant was not observed in every race.' }

  Write-Host "`nComplete: $($Summary.passed_trials)/$($Summary.total_trials) passed" -ForegroundColor Green
  Write-Host 'Observed races: 8/8 overlap, 8/8 single accept, 0 CAS overlap' -ForegroundColor Green
  Write-Host "Evidence folder: $Output" -ForegroundColor White
  Write-Host 'Both test VMs were left powered off.' -ForegroundColor DarkGray
  Start-Process explorer.exe -ArgumentList $Output
}
finally {
  if ($TranscriptStarted) { try { Stop-Transcript *> $null } catch {} }
  if ($Bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr) }
  if (Test-Path -LiteralPath $PasswordFile) { Remove-Item -LiteralPath $PasswordFile -Force }
}

Read-Host 'Press Enter to close'
