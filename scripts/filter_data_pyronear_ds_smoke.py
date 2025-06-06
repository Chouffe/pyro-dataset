"""
CLI Script to filter data from the pyronear_ds dataset to only
keep images with fire smoke.

The folder structure remains the same, only the non-smoke images are discarded.

Usage:
    python filter_data_pyronear_ds_smoke.py --dir-dataset <path_to_dataset> --save-dir <path_to_save_dir> [--allowed-dataset-prefixes <prefix1> <prefix2> ...] [-log <loglevel>]

Arguments:
    --save-dir: Directory to save the filtered dataset. Default is ./data/interim/filtered/smoke/pyronear_ds_03_2024/.
    --dir-dataset: Directory containing the pyro-sdis dataset. Default is ./data/raw/pyronear_ds_03_2024/.
    --allowed-dataset-prefixes: Set of allowed data prefixes to use. Default is ["pyronear", "awf", "random", "adf"].
    -log, --loglevel: Provide logging level. Example --loglevel debug, default=warning.
"""

import argparse
import logging
import shutil
from pathlib import Path

from tqdm import tqdm


def make_cli_parser() -> argparse.ArgumentParser:
    """
    Make the CLI parser.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--save-dir",
        help="directory to save the filtered dataset.",
        type=Path,
        default=Path("./data/interim/filtered/smoke/pyronear_ds_03_2024/"),
    )
    parser.add_argument(
        "--dir-dataset",
        help="directory containing the pyro-sdis dataset.",
        type=Path,
        default=Path("./data/raw/pyronear_ds_03_2024/"),
    )
    parser.add_argument(
        "--allowed-dataset-prefixes",
        help="Set of allowed data prefixes to use.",
        nargs="+",
        type=str,
        default=["pyronear", "awf", "random", "adf"],
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


def filepath_image_to_filepath_label(filepath_image: Path) -> Path:
    """
    Given a filepath_image it returns its associated filepath_label.

    Returns:
        filepath_label (Path): the associated label filepath.
    """
    return Path(str(filepath_image).replace("images", "labels").replace(".jpg", ".txt"))


def list_dataset_images(dir_dataset: Path) -> list[Path]:
    """
    List all images from the `dir_dataset`

    Returns:
        filepaths (list[Path]): all image filepaths from dir_dataset.
    """
    return list(dir_dataset.glob("**/*.jpg"))


def has_smoke(filepath_label: Path) -> bool:
    """
    Does the `filepath_label` contain a smoke?

    Returns:
        has_smoke? (bool): whether or not the filepath has a smoke detected in it.
    """
    return (
        filepath_label.exists()
        and filepath_label.is_file()
        and filepath_label.stat().st_size > 0
    )


def has_dataset_prefix(filepath_image: Path, allowed_prefixes: list[str]) -> bool:
    """
    Does the filepath_image contain the allowed prefix?

    Returns:
        has_prefix? (bool): whether or not the filepath has the prefix in it.
    """
    prefix = filepath_image.name.split("_")[0].lower()
    return prefix in allowed_prefixes


def filter_dataset(
    filepaths_images: list[Path],
    allowed_dataset_prefixes: list[str],
) -> list[Path]:
    """
    Filter the list of images that contain fire smoke.

    Returns:
        filepaths (list[Path]): List of image filepaths that contain smoke.
    """
    filepaths_images_with_smoke = []
    for filepath_image in tqdm(filepaths_images):
        filepath_label = filepath_image_to_filepath_label(filepath_image)
        if has_smoke(filepath_label=filepath_label) and has_dataset_prefix(
            filepath_image=filepath_image, allowed_prefixes=allowed_dataset_prefixes
        ):
            filepaths_images_with_smoke.append(filepath_image)

    return filepaths_images_with_smoke


def copy_over(filepaths_images: list[Path], save_dir: Path, dir_dataset: Path) -> None:
    """
    Copy the filepaths_images over to the save dir along with their filepaths labels.

    Returns:
        None
    """
    for filepath_image in tqdm(filepaths_images):
        filepath_label = filepath_image_to_filepath_label(filepath_image)
        filepath_image_destination = save_dir / filepath_image.relative_to(dir_dataset)
        filepath_label_destination = save_dir / filepath_label.relative_to(dir_dataset)
        filepath_image_destination.parent.mkdir(parents=True, exist_ok=True)
        filepath_label_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(filepath_image, filepath_image_destination)
        shutil.copy(filepath_label, filepath_label_destination)


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
        allowed_dataset_prefixes = args["allowed_dataset_prefixes"]
        logger.info(f"filtering smokes and saving results in {save_dir}")
        save_dir.mkdir(parents=True, exist_ok=True)
        filepaths_images = list_dataset_images(dir_dataset)
        logger.info(f"found {len(filepaths_images)} images in {dir_dataset}")
        filepaths_images_with_smoke = filter_dataset(
            filepaths_images=filepaths_images,
            allowed_dataset_prefixes=allowed_dataset_prefixes,
        )
        logger.info(
            f"found {len(filepaths_images_with_smoke)} images with smoke in {dir_dataset}"
        )
        logger.info(f"copy over images and labels.")
        copy_over(
            filepaths_images=filepaths_images_with_smoke,
            save_dir=save_dir,
            dir_dataset=dir_dataset,
        )
        exit(0)
