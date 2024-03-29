import subprocess
import os
import argparse
import re

# execute adb command and return stdout
def run_adb_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"{output.decode().strip()}")
    
    return output.decode().strip().replace('\r', '')

# get device serials from "adb devices"
def get_device_serials():
    command = 'adb devices'
    output = run_adb_command(command)
    devices = output.split('\n')[1:]
    device_serials = [device.split('\t')[0] for device in devices if device]
    return device_serials

# get all package list
def get_installed_packages(device_serial):
    if device_serial:
        command = f'adb -s {device_serial} shell pm list packages'
    else:
        command = 'adb shell pm list packages'
    output = run_adb_command(command)
    packages = output.split('\n')
    package_names = [package.split(':')[1] for package in packages if package]
    return package_names


# get packages version
def get_installed_packages_version(device_serial):
    adb_command = """dumpsys package | awk '/^Packages\:/,/^$/ { if ($0 ~ /^[ ]*Package \[.*\] (.*)/) { i = index($0, ""["") + 1; pkg = substr($0, i, index($0, ""]"") - i); printf ""%s\t"", pkg; } else if($0 ~ /^[ ]*versionName=(.*)/) { print }}'"""
    if device_serial:
        command = f'adb -s {device_serial} shell "{adb_command}"'
    else:
        command = f'adb shell "{adb_command}"'
    output = run_adb_command(command)
    packages_info = {pkg: re.search(r'versionName=([^\s]+)', ver).group(1) for pkg, ver in [line.split('\t') for line in output.split('\n') if line]}
    return packages_info

# get package version name
def get_package_version(package_name, device_serial):
    if device_serial:
        command = f'adb -s {device_serial} shell "dumpsys package {package_name} | grep versionName"'
    else:
        command = f'adb shell "dumpsys package {package_name} | grep versionName"'
    output = run_adb_command(command)
    version_match = re.search(r'versionName=([^\s]+)', output)
    package_version = version_match.group(1) if version_match else None
    return package_version

# get package path
def get_package_paths(package_name, device_serial):
    if device_serial:
        command = f'adb -s {device_serial} shell pm path {package_name}'
    else:
        command = f'adb shell pm path {package_name}'
    output = run_adb_command(command)
    paths = output.split('\n')
    package_paths = [path.replace('package:', '').strip() for path in paths if path.startswith('package:')]
    return package_paths

# backup package to local
def backup_apk(package_name, output_dir, version, device_serial):
    # version = get_package_version(package_name, device_serial)

    package_dir = os.path.join(output_dir, f'{package_name}_{version}')
    os.makedirs(package_dir, exist_ok=True)

    package_paths = get_package_paths(package_name, device_serial)

    for package_path in package_paths:
        output_file = os.path.join(package_dir, '.')

        if device_serial:
            command = f'adb -s {device_serial} pull {package_path} {output_file}'
        else:
            command = f'adb pull {package_path} {output_file}'
        run_adb_command(command)
        # print(command)

# main
def main():
    output_dir = './apk_backups'
    os.makedirs(output_dir, exist_ok=True)

    existed_list = []
    try:
        existed_list = open(os.path.join(output_dir, 'existed_list.txt'), 'r').read().split('\n')
    except:
        pass

    parser = argparse.ArgumentParser(description='APK Backup Tool')
    parser.add_argument('-s', '--serial', help='device serial number')
    parser.add_argument('-d', '--dry-run', action='store_true', help='dry run')
    args = parser.parse_args()

    device_serial = args.serial if args.serial else ''
    device_serials = get_device_serials()

    if not device_serial and len(device_serials) > 1:
        print("Multiple devices connected. Please specify a device serial using the '-s' option:")
        print(device_serials)
        return

    versions_info = get_installed_packages_version(device_serial)

    # packages is subset of versions_info
    packages = get_installed_packages(device_serial)

    for package_name in packages:
        version = versions_info[package_name]
        package_identifier = f'{package_name}_{version}'
        package_dir = os.path.join(output_dir, package_identifier)
        if package_identifier in existed_list or os.path.exists(package_dir):
            continue
        print(package_name, version)
        if args.dry_run:
            continue
        backup_apk(package_name, output_dir, version, device_serial)

if __name__ == '__main__':
    main()
