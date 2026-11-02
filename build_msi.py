"""
Real MSI Package Generator for TinyLytic Studio
Builds a complete, standalone Windows Installer package (.msi) with embedded media1.cab.
Developer: NoishiXzen & Aivory (https://aivorygen.netlify.app | noishixzen@gmail.com)
"""
import os
import sys
import subprocess
import tempfile
import win32com.client

def build_real_msi():
    base_dir = r"K:\Webapps Projects\TinyLytic - Build\5 latest one"
    out_dir = os.path.join(base_dir, "Installers_Output")
    os.makedirs(out_dir, exist_ok=True)
    msi_path = os.path.join(out_dir, "TinyLytic_Setup_v2.0.msi")

    if os.path.exists(msi_path):
        try:
            os.remove(msi_path)
        except Exception:
            pass

    # 1. Gather all files to include in the payload
    include_files = [
        ("Tinylytic.py", "Tinylytic.py"),
        ("core_engine.py", "core_engine.py"),
        ("workers.py", "workers.py"),
        ("chat_engine.py", "chat_engine.py"),
        ("video_caption_studio.py", "video_caption_studio.py"),
        ("vision_engine.py", "vision_engine.py"),
        ("uninstaller.py", "uninstaller.py"),
        ("installer_wizard.py", "installer_wizard.py"),
        ("requirements.txt", "requirements.txt"),
        ("merges.txt", "merges.txt"),
        ("app_icon.ico", "app_icon.ico"),
        ("icon.ico", "icon.ico"),
        ("Activation Key.txt", "Activation_Key.txt"),
        ("activated.flag", "activated.flag"),
        ("llama.dll", "llama.dll"),
        ("llama.lib", "llama.lib"),
        (os.path.join("assets", "tokenizer.json"), "assets_tokenizer.json"),
        (os.path.join("assets", "tokenizer_config.json"), "assets_tokenizer_config.json"),
        (os.path.join("assets", "vocab.json"), "assets_vocab.json"),
        (os.path.join("assets", "config.json"), "assets_config.json"),
    ]

    valid_files = []
    for rel_src, cab_dest in include_files:
        full_src = os.path.join(base_dir, rel_src)
        if os.path.exists(full_src):
            size = os.path.getsize(full_src)
            valid_files.append((full_src, rel_src, cab_dest, size))

    print(f"Collected {len(valid_files)} files for packaging into MSI cabinet.")

    # 2. Build media1.cab using makecab.exe
    temp_dir = tempfile.mkdtemp()
    ddf_path = os.path.join(temp_dir, "cabinet.ddf")
    cab_path = os.path.join(temp_dir, "media1.cab")

    with open(ddf_path, "w", encoding="utf-8") as ddf:
        ddf.write(".Set CabinetNameTemplate=media1.cab\n")
        ddf.write(f".Set DiskDirectory1={temp_dir}\n")
        ddf.write(".Set MaxDiskSize=CDROM\n")
        ddf.write(".Set Cabinet=on\n")
        ddf.write(".Set Compress=on\n")
        ddf.write(".Set CompressionType=MSZIP\n")
        for full_src, rel_src, cab_dest, size in valid_files:
            ddf.write(f'"{full_src}" {cab_dest}\n')

    cmd = ["makecab.exe", "/F", ddf_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(cab_path):
        print(f"makecab error: {res.stderr}")
        raise RuntimeError("Cabinet creation failed.")

    cab_size = os.path.getsize(cab_path)
    print(f"Created media1.cab successfully. Cabinet Size: {cab_size / (1024*1024):.2f} MB ({cab_size} bytes)")

    # 3. Create Windows Installer Database
    installer = win32com.client.Dispatch("WindowsInstaller.Installer")
    db = installer.OpenDatabase(msi_path, 3)

    def run_sql(sql):
        v = db.OpenView(sql)
        v.Execute()
        v.Close()

    # 3.1 Property Table
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

    # 3.2 Directory Table
    run_sql("CREATE TABLE `Directory` (`Directory` CHAR(72) NOT NULL, `Directory_Parent` CHAR(72), `DefaultDir` CHAR(255) NOT NULL PRIMARY KEY `Directory`)")
    run_sql("INSERT INTO `Directory` (`Directory`, `DefaultDir`) VALUES ('TARGETDIR', 'SourceDir')")
    run_sql("INSERT INTO `Directory` (`Directory`, `Directory_Parent`, `DefaultDir`) VALUES ('LocalAppDataFolder', 'TARGETDIR', '.')")
    run_sql("INSERT INTO `Directory` (`Directory`, `Directory_Parent`, `DefaultDir`) VALUES ('INSTALLDIR', 'LocalAppDataFolder', 'TinyLytic_Studio')")

    # 3.3 Component Table
    run_sql("CREATE TABLE `Component` (`Component` CHAR(72) NOT NULL, `ComponentId` CHAR(38), `Directory_` CHAR(72) NOT NULL, `Attributes` SHORT NOT NULL, `Condition` CHAR(255), `KeyPath` CHAR(72) PRIMARY KEY `Component`)")
    run_sql("INSERT INTO `Component` (`Component`, `ComponentId`, `Directory_`, `Attributes`, `KeyPath`) VALUES ('MainComponent', '{7E4D3E71-6C2A-4B6A-914F-5D9183F204C1}', 'INSTALLDIR', 0, 'f_Tinylytic_py')")

    # 3.4 Feature Table
    run_sql("CREATE TABLE `Feature` (`Feature` CHAR(38) NOT NULL, `Feature_Parent` CHAR(38), `Title` CHAR(64), `Description` CHAR(255), `Display` SHORT NOT NULL, `Level` SHORT NOT NULL, `Directory_` CHAR(72), `Attributes` SHORT NOT NULL PRIMARY KEY `Feature`)")
    run_sql("INSERT INTO `Feature` (`Feature`, `Title`, `Description`, `Display`, `Level`, `Directory_`, `Attributes`) VALUES ('MainFeature', 'TinyLytic Studio', 'Installs TinyLytic Studio speech AI application.', 1, 1, 'INSTALLDIR', 0)")

    # 3.5 FeatureComponents Table
    run_sql("CREATE TABLE `FeatureComponents` (`Feature_` CHAR(38) NOT NULL, `Component_` CHAR(72) NOT NULL PRIMARY KEY `Feature_`, `Component_`)")
    run_sql("INSERT INTO `FeatureComponents` (`Feature_`, `Component_`) VALUES ('MainFeature', 'MainComponent')")

    # 3.6 Media Table
    last_seq = len(valid_files)
    run_sql("CREATE TABLE `Media` (`DiskId` SHORT NOT NULL, `LastSequence` SHORT NOT NULL, `DiskPrompt` CHAR(64), `Cabinet` CHAR(255), `VolumeLabel` CHAR(32), `Source` CHAR(72) PRIMARY KEY `DiskId`)")
    run_sql(f"INSERT INTO `Media` (`DiskId`, `LastSequence`, `DiskPrompt`, `Cabinet`) VALUES (1, {last_seq}, 'Disk 1', '#media1.cab')")

    # 3.7 File Table
    run_sql("CREATE TABLE `File` (`File` CHAR(72) NOT NULL, `Component_` CHAR(72) NOT NULL, `FileName` CHAR(255) NOT NULL, `FileSize` LONG NOT NULL, `Version` CHAR(72), `Language` CHAR(20), `Attributes` SHORT, `Sequence` SHORT NOT NULL PRIMARY KEY `File`)")
    for idx, (full_src, rel_src, cab_dest, size) in enumerate(valid_files, 1):
        file_key = f"f_{cab_dest.replace('.', '_')}"
        file_name = os.path.basename(rel_src)
        # Attributes: 512 = msidbFileAttributesCompressed (stored in cabinet)
        run_sql(f"INSERT INTO `File` (`File`, `Component_`, `FileName`, `FileSize`, `Attributes`, `Sequence`) VALUES ('{file_key}', 'MainComponent', '{file_name}', {size}, 512, {idx})")

    # 3.8 InstallExecuteSequence Table
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

    # 3.9 Embed media1.cab into _Streams Table
    view = db.OpenView("INSERT INTO `_Streams` (`Name`, `Data`) VALUES ('media1.cab', ?)")
    record = installer.CreateRecord(1)
    record.SetStream(1, cab_path)
    view.Execute(record)
    view.Close()

    # Commit and finalize database
    db.Commit()

    final_size = os.path.getsize(msi_path)
    print(f"[OK] Successfully built standalone MSI package: {msi_path}")
    print(f"Final MSI File Size: {final_size / (1024*1024):.2f} MB ({final_size} bytes)")
    return msi_path

if __name__ == "__main__":
    build_real_msi()
