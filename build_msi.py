"""
MSI Package Generator for TinyLytic Studio
Builds a standard Windows Installer package (.msi) using direct Windows Installer SQL.
Developer: NoishiXzen & Aivory (https://aivorygen.netlify.app | noishixzen@gmail.com)
"""
import os
import sys
import win32com.client

def build_msi():
    out_dir = r"K:\Webapps Projects\TinyLytic - Build\5 latest one\Installers_Output"
    os.makedirs(out_dir, exist_ok=True)
    msi_path = os.path.join(out_dir, "TinyLytic_Setup_v2.0.msi")

    if os.path.exists(msi_path):
        try:
            os.remove(msi_path)
        except Exception:
            pass

    installer = win32com.client.Dispatch("WindowsInstaller.Installer")
    db = installer.OpenDatabase(msi_path, 3)

    def run_sql(sql):
        v = db.OpenView(sql)
        v.Execute()
        v.Close()

    # 1. Property Table
    run_sql("CREATE TABLE `Property` (`Property` CHAR(72) NOT NULL, `Value` CHAR(0) NOT NULL PRIMARY KEY `Property`)")

    props = [
        ("ProductName", "TinyLytic Studio"),
        ("ProductVersion", "2.0.0"),
        ("Manufacturer", "NoishiXzen & Aivory"),
        ("ProductCode", "{E58E971B-A795-4BD9-9BCE-DF6B8E5F7E81}"),
        ("UpgradeCode", "{B8933E1D-1F0A-4E3F-8C7E-28681B3476E2}"),
        ("ARPHELPLINK", "https://aivorygen.netlify.app"),
        ("ARPURLINFOABOUT", "https://aivorygen.netlify.app"),
        ("ARPCONTACT", "noishixzen@gmail.com"),
        ("ARPCOMMENTS", "TinyLytic Studio Speech & AI Assistant Suite"),
        ("ALLUSERS", "2"),
        ("MSIINSTALLPERUSER", "1"),
        ("SecureCustomProperties", "WIX_DOWNGRADE_DETECTED;WIX_UPGRADE_DETECTED")
    ]
    for k, v in props:
        run_sql(f"INSERT INTO `Property` (`Property`, `Value`) VALUES ('{k}', '{v}')")

    # 2. Directory Table
    run_sql("CREATE TABLE `Directory` (`Directory` CHAR(72) NOT NULL, `Directory_Parent` CHAR(72), `DefaultDir` CHAR(255) NOT NULL PRIMARY KEY `Directory`)")
    run_sql("INSERT INTO `Directory` (`Directory`, `DefaultDir`) VALUES ('TARGETDIR', 'SourceDir')")
    run_sql("INSERT INTO `Directory` (`Directory`, `Directory_Parent`, `DefaultDir`) VALUES ('LocalAppDataFolder', 'TARGETDIR', '.')")
    run_sql("INSERT INTO `Directory` (`Directory`, `Directory_Parent`, `DefaultDir`) VALUES ('INSTALLDIR', 'LocalAppDataFolder', 'TinyLytic_Studio')")

    # 3. Component Table
    run_sql("CREATE TABLE `Component` (`Component` CHAR(72) NOT NULL, `ComponentId` CHAR(38), `Directory_` CHAR(72) NOT NULL, `Attributes` SHORT NOT NULL, `Condition` CHAR(255), `KeyPath` CHAR(72) PRIMARY KEY `Component`)")
    run_sql("INSERT INTO `Component` (`Component`, `ComponentId`, `Directory_`, `Attributes`, `KeyPath`) VALUES ('MainComponent', '{7E4D3E71-6C2A-4B6A-914F-5D9183F204C1}', 'INSTALLDIR', 0, 'Tinylytic.py')")

    # 4. Feature Table
    run_sql("CREATE TABLE `Feature` (`Feature` CHAR(38) NOT NULL, `Feature_Parent` CHAR(38), `Title` CHAR(64), `Description` CHAR(255), `Display` SHORT NOT NULL, `Level` SHORT NOT NULL, `Directory_` CHAR(72), `Attributes` SHORT NOT NULL PRIMARY KEY `Feature`)")
    run_sql("INSERT INTO `Feature` (`Feature`, `Title`, `Description`, `Display`, `Level`, `Directory_`, `Attributes`) VALUES ('MainFeature', 'TinyLytic Studio', 'Installs TinyLytic Studio speech AI application.', 1, 1, 'INSTALLDIR', 0)")

    # 5. FeatureComponents Table
    run_sql("CREATE TABLE `FeatureComponents` (`Feature_` CHAR(38) NOT NULL, `Component_` CHAR(72) NOT NULL PRIMARY KEY `Feature_`, `Component_`)")
    run_sql("INSERT INTO `FeatureComponents` (`Feature_`, `Component_`) VALUES ('MainFeature', 'MainComponent')")

    # 6. Media Table
    run_sql("CREATE TABLE `Media` (`DiskId` SHORT NOT NULL, `LastSequence` SHORT NOT NULL, `DiskPrompt` CHAR(64), `Cabinet` CHAR(255), `VolumeLabel` CHAR(32), `Source` CHAR(72) PRIMARY KEY `DiskId`)")
    run_sql("INSERT INTO `Media` (`DiskId`, `LastSequence`, `DiskPrompt`, `Cabinet`) VALUES (1, 100, 'Disk 1', '#media1.cab')")

    # 7. InstallExecuteSequence Table
    run_sql("CREATE TABLE `InstallExecuteSequence` (`Action` CHAR(72) NOT NULL, `Condition` CHAR(255), `Sequence` SHORT PRIMARY KEY `Action`)")
    seq = [
        ("CostInitialize", 800),
        ("FileCost", 900),
        ("CostFinalize", 1000),
        ("InstallValidate", 1400),
        ("InstallInitialize", 1500),
        ("ProcessComponents", 1600),
        ("UnpublishFeatures", 1800),
        ("RemoveFiles", 3500),
        ("InstallFiles", 4000),
        ("RegisterProduct", 6100),
        ("PublishFeatures", 6300),
        ("PublishProduct", 6400),
        ("InstallFinalize", 6600)
    ]
    for act, s in seq:
        run_sql(f"INSERT INTO `InstallExecuteSequence` (`Action`, `Sequence`) VALUES ('{act}', {s})")

    # Commit database
    db.Commit()
    print(f"[OK] Successfully built MSI package: {msi_path}")
    return msi_path

if __name__ == "__main__":
    build_msi()
