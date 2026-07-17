import os
import sys
import json
import urllib.request
from pathlib import Path

def download_paper():
    server_dir = Path("server")
    server_dir.mkdir(exist_ok=True)
    
    headers = {'User-Agent': 'MinecraftServerInstaller/1.0 (contact@example.com)'}
    
    # We will try the new API v3 first, then fallback to v2
    apis = [
        ("v3", "https://fill.papermc.io/v3/projects/paper"),
        ("v2", "https://api.papermc.io/v2/projects/paper")
    ]
    
    version = None
    build = None
    download_url = None
    
    for api_version, api_url in apis:
        print(f"Trying to get versions from {api_version} API...")
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read().decode('utf-8'))
                
                # Get the latest Minecraft version
                minecraft_keys = []
                for k in data['versions'].keys():
                    try:
                        minecraft_keys.append(([int(c) for c in k.split('.')], k))
                    except ValueError:
                        pass
                minecraft_keys.sort()
                latest_major = minecraft_keys[-1][1]
                
                versions_list = data['versions'][latest_major]
                stable_versions = [v for v in versions_list if not any(x in v.lower() for x in ['rc', 'pre', 'beta', 'alpha'])]
                if not stable_versions:
                    stable_versions = versions_list
                version = stable_versions[0]
                print(f"Found latest stable version: {version}")
                
                # Get builds
                if api_version == "v3":
                    builds_url = f"https://fill.papermc.io/v3/projects/paper/versions/{version}/builds"
                else:
                    builds_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
                
                req2 = urllib.request.Request(builds_url, headers=headers)
                with urllib.request.urlopen(req2) as res2:
                    builds_data = json.loads(res2.read().decode('utf-8'))
                    if isinstance(builds_data, list):
                        print("builds_data is list. Length:", len(builds_data))
                        if builds_data:
                            print("Sample build:", builds_data[-1])
                    else:
                        print("Builds data keys:", list(builds_data.keys()))
                    
                    if api_version == "v3":
                        builds = builds_data if isinstance(builds_data, list) else builds_data.get('builds', [])
                        # Filter stable builds case-insensitively
                        stable_builds = [b for b in builds if b.get('channel', '').lower() == 'stable']
                        if not stable_builds:
                            stable_builds = builds  # fallback to all builds
                        
                        latest_build = stable_builds[-1]
                        build = latest_build.get('build', latest_build.get('id'))
                        
                        downloads = latest_build.get('downloads', {})
                        dl_key = None
                        for k in ['server:default', 'application', 'server']:
                            if k in downloads:
                                dl_key = k
                                break
                        if not dl_key and downloads:
                            dl_key = list(downloads.keys())[0]
                            
                        if dl_key:
                            dl_info = downloads[dl_key]
                            if 'url' in dl_info:
                                url_path = dl_info['url']
                                if url_path.startswith('http'):
                                    download_url = url_path
                                else:
                                    if not url_path.startswith('/'):
                                        url_path = '/' + url_path
                                    download_url = f"https://fill-data.papermc.io{url_path}"
                            else:
                                download_name = dl_info['name']
                                download_url = f"https://fill-data.papermc.io/v3/projects/paper/versions/{version}/builds/{build}/downloads/{download_name}"
                    else:
                        # v2
                        builds = builds_data.get('builds', [])
                        build = builds[-1]
                        download_name = f"paper-{version}-{build}.jar"
                        download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build}/downloads/{download_name}"
                    
                    if download_url:
                        print(f"Found build: {build}")
                        print(f"Download URL: {download_url}")
                        break
        except Exception as e:
            import traceback
            print(f"Failed to fetch from {api_version} API: {e}")
            traceback.print_exc()
            continue
            
    if not download_url:
        print("Error: Could not retrieve download URL from any PaperMC API version.")
        sys.exit(1)
        
    # Download the jar
    jar_path = server_dir / "server.jar"
    print(f"Downloading Paper {version} build {build} to {jar_path}...")
    try:
        req_dl = urllib.request.Request(download_url, headers=headers)
        with urllib.request.urlopen(req_dl) as res_dl:
            with open(jar_path, 'wb') as f:
                f.write(res_dl.read())
        print("Download complete!")
    except Exception as e:
        print(f"Error downloading jar: {e}")
        sys.exit(1)
        
    # Create EULA
    eula_path = server_dir / "eula.txt"
    print(f"Creating eula.txt with eula=true...")
    with open(eula_path, 'w', encoding='utf-8') as f:
        f.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
        f.write("eula=true\n")
        
    # Create start scripts
    print("Creating start.bat...")
    with open(server_dir / "start.bat", "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write("java -Xms2G -Xmx2G -jar server.jar nogui\n")
        f.write("pause\n")
        
    print("Creating start.sh...")
    with open(server_dir / "start.sh", "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\n")
        f.write("java -Xms2G -Xmx2G -jar server.jar nogui\n")
        
    print("\nInstallation successful!")
    print("To start the server, run:")
    print("  cd server")
    print("  start.bat (on Windows) or ./start.sh (on Linux/macOS)")

if __name__ == "__main__":
    download_paper()
