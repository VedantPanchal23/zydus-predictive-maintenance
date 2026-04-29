param(
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$ProjectName = "zydus-pm",
    [switch]$SkipBuilderPrune
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is not available in PATH."
}

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $projectRoot

try {
    Write-Host "[1/5] Stopping compose stack and removing project resources..."
    docker compose -f $ComposeFile -p $ProjectName down --volumes --remove-orphans

    Write-Host "[2/5] Removing legacy zydus containers from old project paths..."
    $containers = docker ps -a --format "{{.Names}}" | Where-Object {
        $_ -match "(?i)zydus|predictive-maintenance"
    }
    if ($containers) {
        docker rm -f $containers
    }
    else {
        Write-Host "No legacy containers found."
    }

    Write-Host "[3/5] Removing legacy zydus volumes..."
    $volumes = docker volume ls --format "{{.Name}}" | Where-Object {
        $_ -match "(?i)zydus|predictive-maintenance"
    }
    if ($volumes) {
        docker volume rm $volumes
    }
    else {
        Write-Host "No legacy volumes found."
    }

    Write-Host "[4/5] Removing legacy zydus networks..."
    $networks = docker network ls --format "{{.Name}}" | Where-Object {
        $_ -match "(?i)zydus|predictive-maintenance"
    }
    if ($networks) {
        foreach ($network in $networks) {
            try {
                docker network rm $network
            }
            catch {
                Write-Host "Skipping network '$network' (in use or already removed)."
            }
        }
    }
    else {
        Write-Host "No legacy networks found."
    }

    if (-not $SkipBuilderPrune) {
        Write-Host "[5/5] Pruning dangling build cache..."
        docker builder prune -f
    }
    else {
        Write-Host "[5/5] Skipped builder prune."
    }

    Write-Host "Docker reset complete. You can now run: docker compose -f infra/docker-compose.yml up -d --build"
}
finally {
    Pop-Location
}
