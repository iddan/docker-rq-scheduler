import sys
import logging
import os
from multiprocessing.dummy import Pool
import requests
import docker
from docker.errors import BuildError

IMAGE = os.getenv("IMAGE")
PACKAGE = os.getenv("PACKAGE")
THREADS = os.getenv("THREADS", 20)

logging.basicConfig(level=logging.INFO)

python_version = "3.6"

bases = {"", "stretch", "slim", "jessie", "slim-jessie", "alpine"}


def get_versions(package):
    response = requests.get(f"https://pypi.python.org/pypi/{package}/json")
    response.raise_for_status()
    info = response.json()
    return list(info["releases"].keys())


def base_to_postfix(base):
    return "-" + base if base else ""


def base_to_python(base):
    return f"python:{python_version + base_to_postfix(base)}"


logging.info("Fetching versions...")
versions = get_versions(PACKAGE)
latest_version = versions[-1]

client = docker.from_env()


def pull_base(base):
    logging.info(f"Pulling {base}")
    client.images.pull(base_to_python(base))


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
        latest_tag = postfix if postfix else "latest"
        image.tag(IMAGE, latest_tag)
        push(IMAGE, latest_tag)


combinations = [(version, base) for version in versions for base in bases]

with Pool(processes=THREADS) as pool:
    pool.map(pull_base, bases)
    pool.starmap(make_version, combinations)
