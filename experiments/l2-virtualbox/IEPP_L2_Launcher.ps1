param(
  [switch]$CheckOnly,
  [string]$VMName,
  [string]$GuestUser,
  [ValidateSet('auto', 'linux', 'windows')]
  [string]$GuestOS = 'auto',
  [string]$GuestNode = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step([string]$Text) { Write-Host "`n[IEPP] $Text" -ForegroundColor Cyan }
function Find-Program([string]$Name, [string[]]$Candidates) {
  $command = Get-Command $Name -ErrorAction SilentlyContinue
  if ($command) { return $command.Source }
  foreach ($candidate in $Candidates) { if (Test-Path -LiteralPath $candidate) { return $candidate } }
  return $null
}

Write-Host 'IEPP L2 VirtualBox 22-Trial Batch' -ForegroundColor White
Write-Host 'Real VM snapshot-restore test - runner v0.2.3' -ForegroundColor DarkGray

$Node = Find-Program 'node.exe' @('C:\Program Files\nodejs\node.exe')
$VBox = Find-Program 'VBoxManage.exe' @('C:\Program Files\Oracle\VirtualBox\VBoxManage.exe')

Write-Step 'Host preflight'
if ($Node) { Write-Host "  [PASS] Node: $(& $Node --version)" -ForegroundColor Green } else { Write-Host '  [FAIL] Node.js 22 or newer is required on the host.' -ForegroundColor Red }
if ($VBox) { Write-Host "  [PASS] VirtualBox: $(& $VBox --version)" -ForegroundColor Green } else { Write-Host '  [FAIL] Oracle VM VirtualBox is required.' -ForegroundColor Red }
if (-not $Node -or -not $VBox) {
  Write-Host "`nInstall the missing dependency, then run this file again." -ForegroundColor Yellow
  Read-Host 'Press Enter to close'
  exit 2
}

Write-Step 'Registered VirtualBox VMs'
$VmList = & $VBox list vms
if ($LASTEXITCODE -ne 0) { throw 'Unable to read the VirtualBox VM list.' }
if ($VmList) { $VmList | ForEach-Object { Write-Host "  $_" } } else { Write-Host '  No registered VMs were found.' -ForegroundColor Yellow }

if ($CheckOnly) {
  Write-Host "`nPreflight completed. The live runner supports Ubuntu/Linux and Windows guests." -ForegroundColor Green
  Write-Host 'Before the live run, install Guest Additions and Node.js 22 or newer in the test VM.' -ForegroundColor Green
  Read-Host 'Press Enter to close'
  exit 0
}

if (-not $VMName) { $VMName = Read-Host 'Enter the exact test VM name' }
if (-not $GuestUser) { $GuestUser = Read-Host 'Enter the test-account name inside the guest OS' }
if ([string]::IsNullOrWhiteSpace($VMName) -or [string]::IsNullOrWhiteSpace($GuestUser)) { throw 'Both the VM name and guest account are required.' }

& $VBox showvminfo $VMName --machinereadable *> $null
if ($LASTEXITCODE -ne 0) { throw "VM '$VMName' was not found." }

Write-Host "`nWARNING: This test powers off the VM and restores snapshots. Never run it on an important work VM." -ForegroundColor Yellow
$confirm = Read-Host "Type RUN only if '$VMName' is a disposable test VM"
if ($confirm -cne 'RUN') { Write-Host 'Run cancelled by the user.'; exit 1 }

$SecurePassword = Read-Host 'Enter the VM test-account password (input is hidden)' -AsSecureString
$Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
$PasswordFile = Join-Path ([IO.Path]::GetTempPath()) ('iepp-l2-' + [guid]::NewGuid().ToString('N') + '.txt')
$Output = Join-Path $Root ('evidence-vm-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))

try {
  $PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
  [IO.File]::WriteAllText($PasswordFile, $PlainPassword, [Text.UTF8Encoding]::new($false))
  $Identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
  & icacls.exe $PasswordFile /inheritance:r /grant:r "${Identity}:(F)" *> $null
  $PlainPassword = $null

  Write-Step 'Starting the 22-trial live VM batch'
  $RunnerArgs = @(
    (Join-Path $Root 'run.mjs')
    '--vm'
    $VMName
    '--guest-user'
    $GuestUser
    '--password-file'
    $PasswordFile
    '--guest-os'
    $GuestOS
    '--vboxmanage'
    $VBox
    '--output'
    $Output
  )
  if (-not [string]::IsNullOrWhiteSpace($GuestNode)) { $RunnerArgs += @('--guest-node', $GuestNode) }
  & $Node @RunnerArgs
  if ($LASTEXITCODE -ne 0) { throw 'The 22-trial batch stopped on a fail-closed condition. Preserve the evidence folder and screen error.' }

  Write-Step 'Verifying SHA-256 files and the linked evidence chain'
  & $Node (Join-Path $Root 'verify-bundle.mjs') $Output
  if ($LASTEXITCODE -ne 0) { throw 'Evidence-bundle integrity verification failed.' }

  $Summary = Get-Content -LiteralPath (Join-Path $Output 'summary.json') -Raw | ConvertFrom-Json
  if (-not $Summary.execution.actual_vm_executed) { throw 'actual_vm_executed is false. This bundle cannot be used as live VM evidence.' }
  Write-Host "`nComplete: $($Summary.passed_trials)/$($Summary.total_trials) passed" -ForegroundColor Green
  Write-Host "Evidence folder: $Output" -ForegroundColor White
  Start-Process explorer.exe -ArgumentList $Output
}
finally {
  if ($Bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr) }
  if (Test-Path -LiteralPath $PasswordFile) { Remove-Item -LiteralPath $PasswordFile -Force }
}

Read-Host 'Press Enter to close'
