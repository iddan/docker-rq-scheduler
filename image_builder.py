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


def get_versions(package):
    response = requests.get(f"https://pypi.python.org/pypi/{package}/json")
    response.raise_for_status()
    info = response.json()
    return list(info["releases"].keys())


def _to_config(version, base_name, python_version):
    postfix = "-" + base_name if base_name else ""
    tag = version + postfix
    full_tag = f"{IMAGE}:{version + postfix}"
    base = f"python:{python_version + postfix}"

    return {
        "version": version,
        "base_name": base_name,
        "full_tag": full_tag,
        "tag": tag,
        "additional_tags": [],
        "base": base,
        "python_version": python_version,
    }


def get_configs(package, image, bases, python_version):
    logging.info("Fetching versions...")

    versions = get_versions(package)
    latest_version = versions[-1]

    configs = [
        _to_config(version, base, python_version)
        for version in versions
        for base in bases
    ]

    for config in configs:
        if config["version"] == latest_version:
            latest_tag = config["base_name"] if config["base_name"] else "latest"
            config["additional_tags"].append(latest_tag)

    return configs


client = docker.from_env()


def _base_to_postfix(base):
    return "-" + base if base else ""


def _base_to_python(base):
    return f"python:{python_version + _base_to_postfix(base)}"


def pull_base(base):
    logging.info(f"Pulling {base}")
    client.images.pull(_base_to_python(base))


def _push(repository, tag, **kwargs):
    output = client.images.push(repository, tag, **kwargs)
    logging.info(output)


def build(config):
    version = config["version"]
    full_tag = config["full_tag"]
    tag = config["tag"]
    base = config["base"]

    logging.info(f"Building {tag}...")

    image, _ = client.images.build(
        path=".", tag=full_tag, buildargs={"VERSION": version, "BASE": base}
    )

    return image


def push(config, image):
    tag = config["tag"]

    logging.info(f"Pushing {tag}...")

    _push(IMAGE, tag)

    for additional_tag in config["additional_tags"]:
        logging.info(f"Pushing {additional_tag}...")
        image.tag(IMAGE, additional_tag)
        _push(IMAGE, additional_tag)
