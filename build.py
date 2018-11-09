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
    output = client.images.push(repository, tag, **kwargs)
    logging.info(output)


def make_version(version, base):
    postfix = "-" + base if base else ""
    tag = version + postfix
    fulltag = f"{IMAGE}:{version + postfix}"
    base = f"python:{python_version + postfix}"

    logging.info(f"Building {tag}...")

    try:
        image, _ = client.images.build(
            path=".", tag=fulltag, buildargs={"VERSION": version, "BASE": base}
        )

    except BuildError as error:
        logging.error(error)
        return

    logging.info(f"Pushing {tag}...")

    push(IMAGE, tag)

    if version == latest_version:
        latest_tag = base if base else "latest"

        logging.info(f"Pushing {latest_tag}...")

        image.tag(IMAGE, latest_tag)
        push(IMAGE, latest_tag)


combinations = [(version, base) for version in versions for base in bases]

with Pool(processes=THREADS) as pool:
    pool.map(pull_base, bases)
    pool.starmap(make_version, combinations)
