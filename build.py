import sys
import logging
import os
from multiprocessing.dummy import Pool
import requests
import docker
from docker.errors import BuildError

IMAGE = os.getenv('IMAGE')
PACKAGE = os.getenv('PACKAGE')

logging.basicConfig(level=logging.INFO)

def get_versions(package):
    response = requests.get(f'https://pypi.python.org/pypi/{package}/json')
    response.raise_for_status()
    info = response.json()
    return list(info['releases'].keys())

logging.info('Fetching versions...')
versions = get_versions(PACKAGE)
latest_version = versions[-1]

client = docker.from_env()

def push(repository, tag, **kwargs):
   push_output_stream = client.images.push(repository, tag, stream=True, **kwargs)
   
   for line in push_output_stream:
       sys.stderr.buffer.write(line + b'\n')

def make_version(version):
    logging.info(f"Building {version}...")

    tag = f'{IMAGE}:{version}'
    try:
        image, build_output_stream = client.images.build(path='.', tag=tag, buildargs={'VERSION': version})

    except BuildError as error:
        logging.error(error)
        return

    logging.info(f"Pushing {version}...")
    push_output_stream = push(IMAGE, version)
    
    if version == latest_version:
        logging.info("Pushing latest...")
        image.tag(IMAGE, 'latest')
        push(IMAGE, 'latest')
            
with Pool(processes=len(versions)) as pool:
    pool.map(make_version, versions)