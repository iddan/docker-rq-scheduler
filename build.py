import os
from multiprocessing.dummy import Pool
import image_builder

IMAGE = os.getenv("IMAGE")
PACKAGE = os.getenv("PACKAGE")
THREADS = os.getenv("THREADS", 20)
PYTHON_VERSION = "3.6"

bases = {"", "stretch", "slim", "jessie", "slim-jessie", "alpine"}

configs = image_builder.get_configs(
    package=PACKAGE, image=IMAGE, bases=bases, python_version=PYTHON_VERSION
)

with Pool(processes=THREADS) as pool:
    pool.map(image_builder.pull_base, bases)
    images = pool.map(image_builder.build, configs)
    pool.starmap(image_builder.push, zip(configs, images))
