from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional
from ophyd_async.core import (
    FilenameProvider,
    PathProvider,
    PathInfo,
)
import os
import shortuuid


class YMDGranularity(int, Enum):
    none = 0
    year = 1
    month = 2
    day = 3


def get_beamline_proposals_dir():
    """
    Function that computes path to the proposals directory based on TLA env vars
    """

    beamline_tla = os.getenv(
        'ENDSTATION_ACRONYM', 
        os.getenv('BEAMLINE_ACRONYM', '')
    ).lower()
    beamline_proposals_dir = (
        Path(f"/nsls2/data/{beamline_tla}/proposals/")
    )

    return beamline_proposals_dir


def generate_date_dir_path(
        device_name: Optional[str] = None,
        ymd_separator: str = os.path.sep,
        granularity: YMDGranularity = YMDGranularity.day,
):
    """Helper function that generates ymd path structure"""

    current_date_template = ''
    if granularity == YMDGranularity.day:
        current_date_template = f"%Y{ymd_separator}%m{ymd_separator}%d"
    elif granularity == YMDGranularity.month:
        current_date_template = f"%Y{ymd_separator}%m"
    elif granularity == YMDGranularity.year:
        current_date_template = f"%Y{ymd_separator}"

    current_date = date.today().strftime(current_date_template)

    if device_name is None:
        ymd_dir_path = current_date
    else:
        ymd_dir_path = os.path.join(
            device_name,
            current_date,
        )

    return ymd_dir_path


class ProposalNumYMDPathProvider(PathProvider):
    def __init__(
        self, filename_provider: FilenameProvider,
        metadata_dict: dict, 
        granularity: YMDGranularity = YMDGranularity.day,
        separator = os.path.sep,
        **kwargs
    ):
        self._filename_provider = filename_provider
        self._metadata_dict = metadata_dict
        self._granularity = granularity
        self._ymd_separator = separator
        self._beamline_proposals_dir = get_beamline_proposals_dir()
        super().__init__(filename_provider, **kwargs)

    def _create_ymd_device_dirpath(self, device_name: str = None) -> Path:
        directory_path = (
            self._beamline_proposals_dir
            / self._metadata_dict["cycle"]
            / self._metadata_dict["data_session"]
            / "assets"
            / generate_date_dir_path(
                device_name=device_name,
                ymd_separator = self._ymd_separator,
                granularity=self._granularity
              )
        )

        return directory_path

    def __call__(self, device_name: str = None) -> PathInfo:

        directory_path = self._create_ymd_device_dirpath(device_name = device_name)

        return PathInfo(
            directory_path = directory_path,
            filename = self._filename_provider(),
            create_dir_depth = - self._granularity,
        )


class ProposalNumScanNumPathProvider(ProposalNumYMDPathProvider):
    def __init__(
        self, filename_provider: FilenameProvider,
        metadata_dict: dict,
        base_name: str = "scan",
        granularity: YMDGranularity = YMDGranularity.none,
        ymd_separator = os.path.sep,
        **kwargs
    ):

        self._base_name = base_name
        super().__init__(
            filename_provider,
            metadata_dict,
            granularity = granularity,
            ymd_separator=ymd_separator,
            **kwargs
        )

    def __call__(self, device_name: Optional[str] = None) -> PathInfo:
        directory_path = self._create_ymd_device_dirpath(device_name = device_name)

        final_dir_path = (
            directory_path / 
            f"{self._base_name}_{self._metadata_dict['scan_id']:06}"
        )

        return PathInfo(
            directory_path = final_dir_path,
            filename = self._filename_provider(),
            # 
            create_dir_depth = - self._granularity - 1,
        )



class ShortUUIDFilenameProvider(FilenameProvider):
    """Generates short uuid filenames with device name as prefix"""

    def __init__(self, separator="_", **kwargs):
        self._separator = separator
        super().__init__(**kwargs)

    def __call__(self, device_name: Optional[str] = None) -> str:
        sid = shortuuid.uuid()
        if device_name is not None:
            return f"{device_name}{self._separator}{sid}"
        else:
            return sid


class DeviceNameFilenameProvider(FilenameProvider):
    """Filename provider that uses device name as filename"""

    def __call__(self, device_name: Optional[str] = None) -> str:
        if device_name is None:
            raise RuntimeError(
                "Device name must be passed in when calling DeviceNameFilenameProvider!"
            )
        return device_name


class NSLS2PathProvider(ProposalNumYMDPathProvider):
    """
    Default NSLS2 path provider
    
    Generates paths in the following format:

    /nsls2/data/{TLA}/proposals/{CYCLE}/{PROPOSAL}/assets/{DETECTOR}/{Y}/{M}/{D}

    Filenames will be {DETECTOR}_{SHORT_UID} followed by the appropriate
    extension as determined by your detector writer.

    Parameters
    ----------
    metadata_dict : dict
        Typically `RE.md`. Used for dynamic save path generation from sync-d experiment
    """

    def __init__(self, *args, **kwargs):
        default_filename_provider = ShortUUIDFilenameProvider()
        super().__init__(default_filename_provider, *args, **kwargs)