import subprocess
import os
import argparse
import re

# execute adb command and return stdout
def run_adb_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, _ = process.communicate()
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
def backup_apk(package_name, output_dir, device_serial):
    version = get_package_version(package_name, device_serial)
    print(package_name, version)
    package_dir = os.path.join(output_dir, f'{package_name}_{version}')
    if os.path.exists(package_dir):
        print('skip')
        return
    package_paths = get_package_paths(package_name, device_serial)
    os.makedirs(package_dir, exist_ok=True)
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

    parser = argparse.ArgumentParser(description='APK Backup Tool')
    parser.add_argument('-s', '--serial', help='device serial number')
    args = parser.parse_args()

    device_serial = args.serial if args.serial else ''
    device_serials = get_device_serials()

    if not device_serial and len(device_serials) > 1:
        print("Multiple devices connected. Please specify a device serial using the '-s' option:")
        print(device_serials)
        return

    packages = get_installed_packages(device_serial)
    for package_name in packages:
        backup_apk(package_name, output_dir, device_serial)

if __name__ == '__main__':
    main()
