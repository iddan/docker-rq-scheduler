import logging
import os
import requests
import docker
from docker.errors import BuildError

logging.basicConfig(level=logging.INFO)

def get_tags(image):
    response = requests.get(f'https://registry.hub.docker.com/v1/repositories/{image}/tags')
    try:
        response.raise_for_status()
        return response.json()
    except:
        return []

def get_versions(package):
    response = requests.get(f'https://pypi.python.org/pypi/{package}/json')
    response.raise_for_status()
    info = response.json()
    return set(info['releases'].keys())

IMAGE = os.getenv('IMAGE')
PACKAGE = os.getenv('PACKAGE')

logging.info('Fetching versions...')
versions = get_versions(PACKAGE)
logging.info('Fetching tags...')
tags = get_tags(IMAGE)
deployed_versions = { tag['name'] for tag in tags }
missing_versions = versions - deployed_versions

client = docker.from_env()

for version in missing_versions:
    try:
        tag = f'{IMAGE}/rq-scheduler:{version}'
        logging.info(f"Building {version}...")
        client.images.build(path='.', tag=tag, buildargs={'VERSION': version})
        logging.info(f"Pushing {version}...")
        client.images.push(IMAGE, version)
    except BuildError as error:
        logging.error(error)