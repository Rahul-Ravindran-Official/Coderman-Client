import glob
import hashlib
import json
import os
import zipfile
from typing import List
import requests
import click

app_version: str = '0.0.18'


@click.group()
def coderman():
    pass

@click.command()
@click.option('--api-key', prompt='API KEY', help='Coderman API Key')
@click.option('--project-name', prompt='PROJECT NAME', help='Unique Name Of The Project')
def init(api_key: str, project_name: str):
    """
    initializes coderman project in the current directory
    """
    write_path: str = get_terminal_cwd() + "/.coderman"
    settings = {
        'version': 1.0,
        'api_key': api_key,
        'project_name': project_name
    }

    json_settings = json.dumps(settings, indent=4, sort_keys=True)
    print('Created Config file @ ' + write_path)
    f = open(write_path, "w")
    f.write(json_settings)
    f.close()


@click.command()
def version():
    """
    Gets the current coderman version
    """
    print('v.' + app_version)


@click.command()
@click.option('--project-name', prompt='Enter Project Name To Delete', help='Project name confirmation')
def destroy(project_name: str):
    """
    Deletes deployed instance of this project
    """

    # No .coderman file
    if check_if_coderman_initialised():
        settings = get_coderman_settings()
    else:
        print('There exists no Coderman project in this directory')
        return

    # .coderman tampering
    if not is_json_tampered(settings):
        json_data = json.loads(settings)
    else:
        print('Your .coderman file has been tampered. Delete it and re-initialize')
        return

    # Server Deletion
    if json_data['project_name'] == project_name:
        print('Project Name Confirmation Successful :)')
        print('Deleting Project On Server ...')
        # TODO delete coderman instance of this project
        print('Deleting .coderman file ...')
        os.remove(get_terminal_cwd() + "/.coderman")
    else:
        print('Project Name Confirmation Failed :(')
        print('Project Name Did Not Match :(')

    track_changes()


@click.command()
def deploy():
    """
    Deploys coderman project in the current directory
    """

    # Strategy :
    # 1. Check if initialised directory else exit
    # 2. Check if Not-synced else exit
    # 3. Check if valid credentials else exit
    # 4. Push the code
    if check_api_key():
        print('OK Deployable.')


@click.command()
@click.option('--recheck', default='False', help='Rechecks the status by tracking all file changes')
@click.option('--pretty-print', default='True', help='Defines the scope of statistics to print.')
def status(recheck: str, pretty_print: str):
    """
    Checks status of current vs deployed code and rechecks if requested
    """

    if recheck == 'True':
        track_changes()

    tracker = read_from_tracker()

    if pretty_print == 'True':
        print('Status : ' + str(tracker['status']))
        print('File-addition : ' + str(tracker['file-addition']))
        print('File-deletion : ' + str(tracker['file-deletion']))
    else:
        print(json.dumps(tracker, indent=4, sort_keys=True))


# CONTEXTUAL HELPER FILES


def track_changes():
    files_grabbed = []

    # No .coderman.tracker file
    try:
        f = open(get_terminal_cwd() + '/.coderman.tracker', 'r')
        full_tracker_contents = f.read()
        f.close()
    except IOError:
        full_tracker_contents = ''
        pass

    # .coderman tampering
    try:
        full_tracker_contents = json.loads(full_tracker_contents)
    except ValueError:
        print('Your .coderman.tracker file has been tampered. Delete it and retry')
        return

    files_grabbed.extend(glob.glob(get_terminal_cwd() + '/**/*.html', recursive=True))
    files_grabbed.extend(glob.glob(get_terminal_cwd() + '/**/*.css', recursive=True))

    file_hash_mapping = {'master_hash': ''}
    master_str = ''

    print(files_grabbed)

    for current_file in files_grabbed:
        f = open(current_file, 'r')
        file_contents = f.read()
        f.close()
        md5_hash = hashlib.md5(file_contents.encode('utf-8')).hexdigest()
        master_str += md5_hash
        file_hash_mapping[current_file[len(get_terminal_cwd()):]] = md5_hash

    # Calculate Master Hash
    master_hash = hashlib.md5(master_str.encode('utf-8')).hexdigest()
    file_hash_mapping['master_hash'] = master_hash

    # Update full_tracker_contents's current and status
    full_tracker_contents['current'] = file_hash_mapping

    if full_tracker_contents['deployed']['master_hash'] == master_hash:
        full_tracker_contents['status'] = 'Synced'
    else:
        full_tracker_contents['status'] = 'Not-Synced'

    # Update full_tracker_contents's
    # + Files Added
    # + Files Deleted
    # + Respective Count
    current = set(full_tracker_contents['current'].keys())
    deployed = set(full_tracker_contents['deployed'].keys())
    files_for_addition = current - deployed
    files_for_deletion = deployed - current

    full_tracker_contents['file-addition-count'] = len(files_for_addition)
    full_tracker_contents['file-deletion-count'] = len(files_for_deletion)
    full_tracker_contents['files-added'] = list(files_for_addition)
    full_tracker_contents['files-deleted'] = list(files_for_deletion)

    # File Changed Compute and Update
    files_changed = []
    for file in full_tracker_contents['deployed']:
        if file in full_tracker_contents['current']:
            if full_tracker_contents['deployed'][file] \
                    != full_tracker_contents['current'][file] and file != 'master_hash':
                files_changed.append(file)

    full_tracker_contents['files-changed'] = files_changed
    full_tracker_contents['file-change-count'] = len(files_changed)

    # Update
    f = open('.coderman.tracker', 'w')
    json_file_hash_mapping = json.dumps(full_tracker_contents, indent=4, sort_keys=True)
    f.write(json_file_hash_mapping)
    f.close()


def read_from_tracker():
    full_tracker_contents = ''

    # No .coderman.tracker file
    if check_if_coderman_tracker_initialised():
        f = open(get_terminal_cwd() + '/.coderman.tracker', 'r')
        full_tracker_contents = f.read()
        f.close()

    # .coderman.tracker tampering
    if not is_json_tampered(full_tracker_contents):
        full_tracker_contents = json.loads(full_tracker_contents)
    else:
        print('Your .coderman.tracker file has been tampered. Delete it and retry')
        return

    return full_tracker_contents


def check_if_coderman_initialised():
    # No .coderman file
    try:
        f = open(get_terminal_cwd() + '/.coderman', 'r')
        f.close()
        return True
    except IOError:
        return False


def check_if_coderman_tracker_initialised():
    # No .coderman.tracker file
    try:
        f = open(get_terminal_cwd() + '/.coderman.tracker', 'r')
        f.close()
        return True
    except IOError:
        return False


def create_zip_folder(the_chosen_files: List[str]):
    """
    :param the_chosen_files: The files required to be included in the zip
    """
    my_zip_file = zipfile.ZipFile(get_terminal_cwd() + "/coderman_temp.zip", "w")

    for f in the_chosen_files:
        my_zip_file.write(get_terminal_cwd() + f, f)


def get_files_to_deploy(tracker: dict) -> List[str]:
    """
    Gets a list of changed files and newly added files
    :return:
    """
    files_to_deploy = []
    files_to_deploy.extend(tracker['files-changed'])
    files_to_deploy.extend(tracker['files-added'])
    return files_to_deploy


def get_coderman_settings():
    f = open('.coderman', 'r')
    settings = f.read()
    f.close()
    return settings


# GENERALISED HELPER FILES


def is_json_tampered(json_string):
    try:
        json.loads(json_string)
        return False
    except ValueError:
        return True


def get_terminal_cwd() -> str:
    return os.getcwd()


def get_api_key():
    try:
        return json.loads(get_coderman_settings)['api_key']
    except:
        return None


def check_api_key() -> bool:
    r = requests.post(
        "http://backendless.io/user/ceac10a0309e60457d2567b349fa872bc913dc2958b9b0a86052f8a2c0752e6e/api/f4f235b2494e414/check_api_key.php",
        data={

        }
    )
    print(str(r.content))
    return str(r.content) == get_api_key


def main():
    coderman.add_command(init)
    coderman.add_command(destroy)
    coderman.add_command(deploy)
    coderman.add_command(status)
    coderman.add_command(version)
    coderman()
