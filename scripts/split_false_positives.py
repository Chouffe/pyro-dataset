"""
CLI Script to perform a data split from the FP_2024 dataset to assign images into a train, val, test split.

The folder structure will follow a ultralytics YOLO scaffolding.

Usage:
    python split_false_positives.py --save-dir <save_directory> --dir-dataset <dataset_directory> --random-seed <seed> [--ratio-train-val <ratio>] [--ratio-val-test <ratio>] [-log <loglevel>]

Arguments:
    --save-dir: Directory to save the splitted dataset.
    --dir-dataset: Directory containing the false positives dataset.
    --random-seed: Random Seed to perform the data split (required).
    --ratio-train-val: Ratio for splitting train and val splits (default: 0.9).
    --ratio-val-test: Ratio for splitting val and test splits (default: 0.5).
    -log, --loglevel: Provide logging level. Example --loglevel debug, default=warning.
"""

import argparse
import logging
import random
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from pyro_dataset.constants import DATE_FORMAT_OUTPUT

# Date format used in the naming of files in FP_2024
DATE_FORMAT_INPUT = "%Y-%m-%dT%H-%M-%S"


@dataclass
class DataSplit:
    """
    Simple class to store the result of the datasplit.

    Attributes:
        train: contains a list of image filepaths and makes the train split.
        val: contains a list of image filepaths and makes the val split.
        test: contains a list of image filepaths and makes the test split.
    """

    train: list[Path]
    val: list[Path]
    test: list[Path]


@dataclass
class ObservationMetadata:
    """
    Simple class to store the metadata of an observation.

    Attributes:
        camera_reference (str): the camera reference (where it was taken)
        datetime (datetime): when it was taken
        azimuth (int): estimated azimuth
    """

    camera_reference: str
    datetime: datetime
    azimuth: int


def make_cli_parser() -> argparse.ArgumentParser:
    """
    Make the CLI parser.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--save-dir",
        help="directory to save the splitted dataset.",
        type=Path,
        default=Path("./data/interim/data-split/false_positives/FP_2024/wise_wolf/"),
    )
    parser.add_argument(
        "--dir-dataset",
        help="directory containing the false positives dataset.",
        type=Path,
        default=Path("./data/interim/filtered/false_positives/FP_2024/wise_wolf/"),
    )
    parser.add_argument(
        "--random-seed",
        help="Random Seed to perform the data split",
        type=int,
        required=True,
        default=0,
    )
    parser.add_argument(
        "--ratio-train-val",
        help="Ratio for splitting train and val splits",
        type=float,
        default=0.9,
    )
    parser.add_argument(
        "--ratio-val-test",
        help="Ratio for splitting val and test splits",
        type=float,
        default=0.5,
    )
    parser.add_argument(
        "-log",
        "--loglevel",
        default="info",
        help="Provide logging level. Example --loglevel debug, default=warning",
    )
    return parser


def validate_parsed_args(args: dict) -> bool:
    """
    Return whether the parsed args are valid.
    """
    if not args["dir_dataset"].exists():
        logging.error(
            f"invalid --dir-dataset, dir {args['dir_dataset']} does not exist"
        )
        return False
    else:
        return True


def make_data_split(
    dir_dataset: Path,
    random_seed: float,
    ratio_train_val: float,
    ratio_val_test: float,
) -> DataSplit:
    """
    Perform the data split for the FP_2024 dataset using the
    provided `random_seed` and the `ratio_train_val`

    __Note__: Prevent train/val leakage by splitting at the folder level.

    Returns:
        data_split (DataSplit): the data split.

    Throws:
        assertError: when the ratios are not in the right ranges (0..1)
    """

    assert 0 <= ratio_train_val <= 1.0, "ratio_train_val should be in (0..1)"
    assert 0 <= ratio_val_test <= 1.0, "ratio_val_test should be in (0..1)"

    rng = random.Random(random_seed)
    folders = list_directories(dir_dataset)
    folders_shuffled = rng.sample(folders, len(folders))
    number_folders = len(folders)

    filepaths_images_train = []
    filepaths_images_val = []
    filepaths_images_test = []

    for idx, folder in enumerate(folders_shuffled):
        filepaths_images = list(folder.glob("**/*.jpg"))
        if idx < number_folders * ratio_train_val:
            filepaths_images_train.extend(filepaths_images)
        elif idx < number_folders * (
            ratio_train_val + (1 - ratio_train_val) * ratio_val_test
        ):
            filepaths_images_val.extend(filepaths_images)
        else:
            filepaths_images_test.extend(filepaths_images)
    return DataSplit(
        train=filepaths_images_train,
        val=filepaths_images_val,
        test=filepaths_images_test,
    )


def list_directories(dir_dataset: Path) -> list[Path]:
    """
    List all directories in the `dir_dataset`.

    Returns:
        dirs (list[Path]): list of directories.
    """
    return [d for d in dir_dataset.iterdir() if d.is_dir()]


def parse_filepath_image(filepath_image: Path) -> ObservationMetadata:
    """
    Given a filepath_image, it returns an ObservationMetadata containing some
    key information about the location and time the picture was taken.


    Returns:
        observation_metadata (ObservationMetadata)
    """
    folder_name = filepath_image.parts[-2]
    camera_group_reference = folder_name.split("_")[2]
    camera_reference = "-".join(camera_group_reference.split("-")[:-1])
    azimuth_str = camera_group_reference.split("-")[-1]
    datetime_str = filepath_image.stem
    return ObservationMetadata(
        camera_reference=camera_reference,
        datetime=datetime.strptime(datetime_str, DATE_FORMAT_INPUT),
        azimuth=int(azimuth_str),
    )


def to_filepath_image_destination(
    save_dir: Path,
    filepath_image: Path,
    split: str,
) -> Path:
    """
    Turn a filepath_image into its filepath destination, adding the proper
    naming convention to it.

    Returns:
        filepath_image_destination (Path)
    """
    observation_metadata = parse_filepath_image(filepath_image)
    filename_prefix = f"pyronear_{observation_metadata.camera_reference}-{observation_metadata.azimuth}".lower()
    filename = f"{filename_prefix}_{observation_metadata.datetime.strftime(DATE_FORMAT_OUTPUT)}.jpg"
    filepath_image_destination = save_dir / "images" / split / filename
    return filepath_image_destination


def to_filepath_label_destination(
    save_dir: Path,
    filepath_image: Path,
    split: str,
) -> Path:
    """
    Turn a filepath_image into its filepath destination, adding the proper
    naming convention to it.

    Returns:
        filepath_label_destination (Path)
    """
    observation_metadata = parse_filepath_image(filepath_image)
    filename_prefix = f"pyronear_{observation_metadata.camera_reference}-{observation_metadata.azimuth}".lower()
    filename = f"{filename_prefix}_{observation_metadata.datetime.strftime(DATE_FORMAT_OUTPUT)}.txt"
    filepath_label_destination = save_dir / "labels" / split / filename
    return filepath_label_destination


def persist_data_split(
    data_split: DataSplit,
    save_dir: Path,
) -> None:
    """
    Persist the data_split in save_dir, structure it in a regular yolo folder structure.

    Returns:
        None
    """
    for split, split_xs in [
        ("train", data_split.train),
        ("val", data_split.val),
        ("test", data_split.test),
    ]:
        for filepath_image in tqdm(split_xs):
            filepath_image_destination = to_filepath_image_destination(
                save_dir=save_dir,
                filepath_image=filepath_image,
                split=split,
            )
            filepath_label_destination = to_filepath_label_destination(
                save_dir=save_dir,
                filepath_image=filepath_image,
                split=split,
            )
            filepath_image_destination.parent.mkdir(parents=True, exist_ok=True)
            filepath_label_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(filepath_image, filepath_image_destination)
            filepath_label_destination.touch()


if __name__ == "__main__":
    cli_parser = make_cli_parser()
    args = vars(cli_parser.parse_args())
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=args["loglevel"].upper())
    if not validate_parsed_args(args):
        exit(1)
    else:
        logging.info(args)
        save_dir = args["save_dir"]
        dir_dataset = args["dir_dataset"]
        random_seed = args["random_seed"]
        ratio_train_val = args["ratio_train_val"]
        ratio_val_test = args["ratio_val_test"]

        logger.info(f"save results in {save_dir}")
        save_dir.mkdir(parents=True, exist_ok=True)
        folders = list_directories(dir_dataset)
        logger.info(f"found {len(folders)} directories in {dir_dataset}")

        logger.info("split the data in train, val, test")
        data_split = make_data_split(
            dir_dataset=dir_dataset,
            random_seed=random_seed,
            ratio_train_val=ratio_train_val,
            ratio_val_test=ratio_val_test,
        )
        logger.info(
            f"datasplit: {len(data_split.train)} images in train - {len(data_split.val)} images in val - {len(data_split.test)} images in test."
        )
        logger.info(f"persist the data split in {save_dir}.")
        persist_data_split(data_split=data_split, save_dir=save_dir)
        exit(0)
