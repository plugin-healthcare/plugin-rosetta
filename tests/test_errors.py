import pytest

from plugin_rosetta import ConfigurationError, RosettaError


def test_package_errors_share_one_base_type() -> None:
    with pytest.raises(RosettaError):
        raise ConfigurationError("invalid configuration")
