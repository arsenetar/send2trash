import sys
import os
from tempfile import NamedTemporaryFile
import pytest

# Only import HOMETRASH on supported platforms
if sys.platform != "win32":
    from send2trash.plat_other import HOMETRASH


@pytest.fixture(name="test_file")
def fixture_test_file():
    file = NamedTemporaryFile(dir=os.path.expanduser("~"), prefix="send2trash_test", delete=False)
    file.close()
    # Verify file was actually created
    assert os.path.exists(file.name) is True
    yield file.name
    # Cleanup trash files on supported platforms
    if sys.platform != "win32":
        name = os.path.basename(file.name)
        # Remove trash files if they exist
        if os.path.exists(os.path.join(HOMETRASH, "files", name)):
            os.remove(os.path.join(HOMETRASH, "files", name))
            os.remove(os.path.join(HOMETRASH, "info", name + ".trashinfo"))
    if os.path.exists(file.name):
        os.remove(file.name)
