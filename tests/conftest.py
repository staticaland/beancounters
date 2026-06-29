"""Shared pytest fixtures for beancounters tests."""

from pathlib import Path

import pytest


# Path fixtures


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """Return the data directory containing bank files."""
    return project_root / "data"


@pytest.fixture
def sparebank1_data_dir(data_dir: Path) -> Path:
    """Return the SpareBank1 data directory."""
    return data_dir / "sparebank1"


@pytest.fixture
def dnb_data_dir(data_dir: Path) -> Path:
    """Return the DNB data directory."""
    return data_dir / "dnb"


@pytest.fixture
def amex_data_dir(data_dir: Path) -> Path:
    """Return the Amex data directory."""
    return data_dir / "amex"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


# Sample file fixtures


@pytest.fixture
def sample_sparebank1_file(sparebank1_data_dir: Path) -> Path:
    """Return a sample SpareBank1 CSV file for testing."""
    return sparebank1_data_dir / "2025-01.csv"


@pytest.fixture
def sample_dnb_file(dnb_data_dir: Path) -> Path:
    """Return a sample DNB Excel file for testing."""
    return dnb_data_dir / "2025-01.xlsx"


@pytest.fixture
def sample_amex_file(amex_data_dir: Path) -> Path:
    """Return a sample Amex QBO file for testing."""
    return amex_data_dir / "2025-01.qbo"


# Importer fixtures


@pytest.fixture
def all_importers():
    """Return all configured importers."""
    from beancounters.importers import get_importers

    return get_importers()


@pytest.fixture
def sparebank1_importer(all_importers):
    """Return the SpareBank1 importer."""
    from beancount_no_sparebank1 import DepositAccountImporter

    for importer in all_importers:
        if isinstance(importer, DepositAccountImporter):
            return importer
    pytest.fail("SpareBank1 importer not found")


@pytest.fixture
def dnb_importer(all_importers):
    """Return the DNB importer."""
    from beancount_no_dnb import Importer as DnbImporter

    for importer in all_importers:
        if isinstance(importer, DnbImporter):
            return importer
    pytest.fail("DNB importer not found")


@pytest.fixture
def amex_importer(all_importers):
    """Return the Amex importer."""
    from beancount_no_amex import Importer as AmexImporter

    for importer in all_importers:
        if isinstance(importer, AmexImporter):
            return importer
    pytest.fail("Amex importer not found")


# Helper fixtures


@pytest.fixture
def all_sparebank1_files(sparebank1_data_dir: Path) -> list[Path]:
    """Return all SpareBank1 CSV files."""
    return sorted(sparebank1_data_dir.glob("*.csv"))


@pytest.fixture
def all_dnb_files(dnb_data_dir: Path) -> list[Path]:
    """Return all DNB Excel files."""
    return sorted(dnb_data_dir.glob("*.xlsx"))


@pytest.fixture
def all_amex_files(amex_data_dir: Path) -> list[Path]:
    """Return all Amex QBO files."""
    return sorted(amex_data_dir.glob("*.qbo"))
