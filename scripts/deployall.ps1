param(
    [Parameter(Mandatory)] [string] $PipelineName,          # Deployment pipeline display name
    [Parameter(Mandatory)] [ValidateSet(0,1)] [int] $SourceStageOrder,  # 0 = Dev->Test, 1 = Test->Prod
    [string] $Note = "Deployed from GitHub Actions"
)

$ErrorActionPreference = 'Stop'

try {
    # --- Credentials (read from environment variables set by the workflow) ---
    $clientId     = $env:PBI_CLIENT_ID
    $clientSecret = $env:PBI_CLIENT_SECRET
    $tenantId     = $env:PBI_TENANT_ID

    $secure = ConvertTo-SecureString $clientSecret -AsPlainText -Force
    $cred   = New-Object System.Management.Automation.PSCredential($clientId, $secure)
    Connect-PowerBIServiceAccount -ServicePrincipal -Credential $cred -Tenant $tenantId | Out-Null

    # --- Get pipelines and find the one by name ---
    $pipelines = (Invoke-PowerBIRestMethod -Url "pipelines" -Method Get | ConvertFrom-Json).value
    $pipeline  = $pipelines | Where-Object { $_.displayName -eq $PipelineName }

    if (-not $pipeline) {
        throw "The pipeline '$PipelineName' was not found. Check the name and that the service principal is an Admin of the pipeline."
    }

    # --- Build request and deploy ---
    $url  = "pipelines/$($pipeline.id)/deployAll"
    $body = @{
        sourceStageOrder = $SourceStageOrder
        options = @{
            allowCreateArtifact    = $true
            allowOverwriteArtifact = $true
        }
        note = $Note
    } | ConvertTo-Json

    $op = Invoke-PowerBIRestMethod -Url $url -Method Post -Body $body | ConvertFrom-Json
    Write-Host "Deployment started. Operation ID: $($op.id)"

    # --- Poll status every 5 seconds ---
    do {
        Start-Sleep -Seconds 5
        $op = Invoke-PowerBIRestMethod -Url "pipelines/$($pipeline.id)/operations/$($op.id)" -Method Get | ConvertFrom-Json
        Write-Host "Status: $($op.status)"
    } while ($op.status -in @('NotStarted', 'Executing'))

    if ($op.status -ne 'Succeeded') {
        Write-Host "---- Deployment details ----"
        $op | ConvertTo-Json -Depth 10 | Write-Host
        throw "Deployment finished with status '$($op.status)'."
    }
    Write-Host "Deployment succeeded."
}
catch {
    Write-Host "::error::$($_.Exception.Message)"
    try { Resolve-PowerBIError -Last } catch {}
    exit 1
}
