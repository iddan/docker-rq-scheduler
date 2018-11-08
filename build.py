import sys
import logging
import os
from multiprocessing.dummy import Pool
import requests
import docker
from docker.errors import BuildError

IMAGE = os.getenv("IMAGE")
PACKAGE = os.getenv("PACKAGE")

logging.basicConfig(level=logging.INFO)

python_version = "3.6"

bases = {
    "",
    "stretch",
    "slim",
    "jessie",
    "slim-jessie",
    "alpine",
    "windowsservercore-ltsc2016",
    "windowsservercore-1709",
}


def get_versions(package):
    response = requests.get(f"https://pypi.python.org/pypi/{package}/json")
    response.raise_for_status()
    info = response.json()
    return list(info["releases"].keys())


logging.info("Fetching versions...")
versions = get_versions(PACKAGE)
latest_version = versions[-1]

client = docker.from_env()


def push(repository, tag, **kwargs):
    push_output_stream = client.images.push(repository, tag, stream=True, **kwargs)

    for line in push_output_stream:
        sys.stderr.buffer.write(line + b"\n")


def make_version(version, base):
    logging.info(f"Building {version} for {base}...")

    postfix = "-" + base if base else ""
    tag = f"{IMAGE}:{version + postfix}"
    base = f"python:{python_version + postfix}"
    try:
        image, _ = client.images.build(
            path=".", tag=tag, buildargs={"VERSION": version, "BASE": base}
        )

    except BuildError as error:
        logging.error(error)
        return

    logging.info(f"Pushing {version}...")
    push(IMAGE, version)

    if version == latest_version:
        logging.info("Pushing latest...")
        image.tag(IMAGE, "latest")
        push(IMAGE, "latest")


combinations = [(version, base) for version in versions for base in bases]

with Pool(processes=len(combinations)) as pool:
    pool.starmap(make_version, combinations)
