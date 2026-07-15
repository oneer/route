# Try to reinstall Microsoft Store
Write-Host "Checking for Microsoft Store packages..."
$storePkg = Get-AppxPackage -AllUsers Microsoft.WindowsStore

if ($storePkg) {
    Write-Host "Found Store package. Re-registering..."
    Get-AppxPackage -AllUsers Microsoft.WindowsStore | ForEach-Object {
        Add-AppxPackage -DisableDevelopmentMode -Register "$($_.InstallLocation)\AppXManifest.xml"
    }
    Write-Host "Microsoft Store re-registered successfully!"
} else {
    Write-Host "Store package not registered for any user. Trying wsreset..."
    wsreset -i
    Start-Sleep -Seconds 5

    # Check if it worked
    $storePkg2 = Get-AppxPackage -AllUsers Microsoft.WindowsStore
    if ($storePkg2) {
        Write-Host "Microsoft Store installed via wsreset!"
    } else {
        Write-Host "Store still missing. Attempting to add from system provisioned packages..."
        $provisioned = Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -like "*Store*" }
        if ($provisioned) {
            $provisioned | ForEach-Object {
                Add-AppxProvisionedPackage -Online -PackagePath $_.InstallLocation -SkipLicense
            }
        } else {
            Write-Host "No provisioned Store package found in system image."
            Write-Host "You may need to run: DISM /Online /Cleanup-Image /RestoreHealth"
            Write-Host "Or download the Microsoft Store installer from Microsoft's website."
        }
    }
}
