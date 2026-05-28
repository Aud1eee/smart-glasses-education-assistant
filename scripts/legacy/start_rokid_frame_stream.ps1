param(
    [ValidateSet("image", "video", "camera")]
    [string]$Source = "image",
    [ValidateSet("lecture", "reading", "note-taking", "review")]
    [string]$TaskMode = "reading",
    [string]$ImagePath = "images\\demo.jpg",
    [string]$VideoPath = "",
    [int]$CameraIndex = 0,
    [double]$Interval = 0.2,
    [double]$Duration = 0,
    [int]$MaxFrames = 0,
    [switch]$LoopVideo,
    [switch]$NoPrepareSession
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "windows_runtime_common.ps1")
$pythonExe = Get-FocusProjectPython -ProjectRoot $projectRoot -RequiredModule "cv2"

Set-Location $projectRoot

Write-FocusProjectRuntimeBanner -PythonExe $pythonExe

$argsList = @(
    "stream_rokid_frames.py",
    "--source", $Source,
    "--task-mode", $TaskMode,
    "--interval", "$Interval"
)

if ($Source -eq "image") {
    $argsList += @("--image-path", $ImagePath)
}
elseif ($Source -eq "video") {
    if ([string]::IsNullOrWhiteSpace($VideoPath)) {
        throw "Provide -VideoPath when using -Source video."
    }
    $argsList += @("--video-path", $VideoPath)
    if ($LoopVideo) {
        $argsList += "--loop-video"
    }
}
elseif ($Source -eq "camera") {
    $argsList += @("--camera-index", "$CameraIndex")
}

if ($Duration -gt 0) {
    $argsList += @("--duration", "$Duration")
}
if ($MaxFrames -gt 0) {
    $argsList += @("--max-frames", "$MaxFrames")
}
if ($NoPrepareSession) {
    $argsList += "--no-prepare-session"
}

& $pythonExe @argsList
